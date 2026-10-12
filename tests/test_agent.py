import asyncio
import json
from dataclasses import replace

import pytest

from decision_lock.agent import MODEL_ERROR, AgentError, DecisionAgent
from decision_lock.config import Settings
from decision_lock.tools import build_tools
from tests.scripted_model import ScriptedModel


def test_real_strands_loop_executes_tool_and_reads_result(store, reply):
    model = ScriptedModel(
        [
            (
                "score_options",
                {
                    "options": [
                        {"name": "Study", "scores": {"fit": 9}},
                        {"name": "Build", "scores": {"fit": 5}},
                    ],
                    "weights": {"fit": 1},
                },
            ),
            ("AgentReply", reply.model_dump()),
        ]
    )
    result = DecisionAgent(Settings(), store, lambda _: model).decide("Study or build?")
    assert result.reply == reply
    assert result.tools[0].name == "score_options"
    assert result.tools[0].result["ranked_options"][0]["weighted_score"] == 9
    tool_results = [
        block["toolResult"]
        for msg in model.requests[1]
        for block in msg["content"]
        if "toolResult" in block
    ]
    assert len(tool_results) == 1
    assert "Study" in json.dumps(tool_results[0])
    assert store.recent() == []  # An agent response never locks by itself.


def test_after_clarification_final_schema_is_used(store, reply):
    model = ScriptedModel([("FinalReply", reply.model_dump())])
    result = DecisionAgent(Settings(), store, lambda _: model).decide(
        "Study or build?",
        clarification="When is the exam?",
        answer="Tomorrow",
    )
    assert result.reply.kind == "recommendation"


def test_history_tool_enforces_permission_even_if_model_calls_it(store, reply):
    store.lock("private", "private problem", reply, "gemini")
    model = ScriptedModel(
        [
            ("get_recent_decisions", {}),
            (
                "AgentReply",
                {"kind": "information", "message": "Enable history to recall decisions."},
            ),
        ]
    )
    result = DecisionAgent(Settings(), store, lambda _: model).decide("What did I lock?")
    assert result.tools[0].result["status"] == "permission_required"
    assert "private problem" not in json.dumps(model.requests)


def test_history_permission_enables_recall(store, reply):
    store.lock("private", "Study or build?", reply, "gemini")
    model = ScriptedModel(
        [
            ("get_recent_decisions", {"limit": 1}),
            ("AgentReply", {"kind": "information", "message": "You locked a study session."}),
        ]
    )
    result = DecisionAgent(Settings(), store, lambda _: model).decide(
        "Recall my last decision",
        allow_history=True,
    )
    assert result.tools[0].result["decisions"][0]["recommendation"] == reply.recommendation


def test_tool_missing_data_reaches_model_as_structured_result(store):
    model = ScriptedModel(
        [
            ("score_options", {"options": [{"name": "A"}, {"name": "B"}], "weights": {"fit": 1}}),
            ("AgentReply", {"kind": "clarification", "message": "How well does each option fit?"}),
        ]
    )
    result = DecisionAgent(Settings(), store, lambda _: model).decide("A or B?")
    assert result.tools[0].result["status"] == "needs_clarification"
    assert "scores for A" in json.dumps(model.requests[1])


def test_time_tool_uses_configured_timezone(store):
    ledger = []
    tools = build_tools(store, "Asia/Kolkata", False, ledger)
    result = tools[1]()
    assert result["timezone"] == "Asia/Kolkata"
    assert result["datetime"].endswith("+05:30")


def test_errors_do_not_expose_exception_payload_in_logs(store, caplog, capsys):
    def failing_model(_):
        raise RuntimeError("credential-secret-sentinel")

    with pytest.raises(AgentError) as caught:
        DecisionAgent(Settings(), store, failing_model).decide("A or B?")
    assert str(caught.value) == MODEL_ERROR
    assert "credential-secret-sentinel" not in caplog.text
    assert "credential-secret-sentinel" not in capsys.readouterr().out


def test_loop_budget_stops_a_repeating_model(store):
    model = ScriptedModel([("get_current_time", {})] * 4)
    agent = DecisionAgent(replace(Settings(), max_model_calls=2), store, lambda _: model)
    with pytest.raises(AgentError, match="could not finish"):
        agent.decide("What tonight?")
    assert len(model.requests) == 2


def test_timeout_is_friendly_and_does_not_hang(store):
    class SlowModel(ScriptedModel):
        async def stream(self, *args, **kwargs):
            await asyncio.sleep(1)
            yield {}

    agent = DecisionAgent(
        replace(Settings(), request_timeout_seconds=0.01), store, lambda _: SlowModel([])
    )
    with pytest.raises(AgentError, match="retry"):
        agent.decide("A or B?")


@pytest.mark.parametrize("code,expected", [(429, "quota"), (403, "rejected"), (404, "unavailable")])
def test_gemini_api_errors_are_sanitized(store, caplog, code, expected):
    class ApiFailure(RuntimeError):
        pass

    def fail(_):
        error = ApiFailure("private-api-key-sentinel")
        error.code = code
        raise error

    with pytest.raises(AgentError, match=expected) as caught:
        DecisionAgent(Settings(), store, fail).decide("A or B?")
    assert "private-api-key-sentinel" not in str(caught.value)
    assert "private-api-key-sentinel" not in caplog.text
