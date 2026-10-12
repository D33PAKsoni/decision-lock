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
            ("FinalReply", reply.model_dump()),
        ]
    )
    result = DecisionAgent(Settings(), store, lambda _: model).decide("Study or build?")
    assert result.reply.model_dump() == reply.model_dump()
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
                "FinalReply",
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
            ("FinalReply", {"kind": "information", "message": "You locked a study session."}),
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
            (
                "ContextReply",
                {
                    "kind": "clarification",
                    "message": "A little context.",
                    "questions": ["How well does each option fit?"],
                },
            ),
        ]
    )
    result = DecisionAgent(Settings(), store, lambda _: model).decide("A or B?", phase="gather")
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
    with pytest.raises(AgentError, match="retry"):
        agent.decide("What tonight?")
    assert len(model.requests) == 1  # One call reserved for native finalization.


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


def test_context_and_review_use_non_recommendation_schemas(store):
    questions = {
        "kind": "clarification",
        "message": "Before comparing.",
        "questions": ["When is the exam?", "How much time?"],
    }
    model = ScriptedModel([("ContextReply", questions)])
    result = DecisionAgent(Settings(), store, lambda _: model).decide(
        "Study or build?", phase="gather"
    )
    assert len(result.reply.questions) == 2
    model = ScriptedModel(
        [("ReviewReply", {"kind": "context", "context_summary": "Exam tomorrow; 30 minutes."})]
    )
    result = DecisionAgent(Settings(), store, lambda _: model).decide(
        "Study or build?", phase="review"
    )
    assert result.reply.kind == "context"


class NativeCompletionModel(ScriptedModel):
    def __init__(self, actions, final_reply):
        super().__init__(actions)
        self.final_reply = final_reply
        self.native_requests = []

    async def structured_output(self, output_model, prompt, **kwargs):
        self.native_requests.append((output_model, prompt))
        yield {"output": output_model.model_validate(self.final_reply)}


def test_tool_limit_finishes_with_native_schema_and_actual_results(store, reply, caplog):
    model = NativeCompletionModel([("get_current_time", {})], reply.model_dump())
    agent = DecisionAgent(replace(Settings(), max_model_calls=2), store, lambda _: model)
    result = agent.decide(
        "Study or build?", reviewed_context="Exam tomorrow; 30 minutes; prioritize passing."
    )
    assert result.reply.kind == "recommendation"
    assert len(model.requests) == 1 and len(model.native_requests) == 1
    schema, messages = model.native_requests[0]
    assert schema.__name__ == "FinalReply"
    data = json.loads(messages[0]["content"][0]["text"])
    assert data["request"]["reviewed_context"].startswith("Exam tomorrow")
    assert data["executed_tools"][0]["name"] == "get_current_time"
    assert result.tools[0].result == data["executed_tools"][0]["result"]
    assert "stop=limit_turns" in caplog.text
    assert "Exam tomorrow" not in caplog.text
    assert store.recent() == []


def test_invalid_structured_tool_output_recovers_without_fake_verdict(store, reply):
    invalid = {"kind": "recommendation", "recommendation": "Study"}
    model = NativeCompletionModel([("FinalReply", invalid)], reply.model_dump())
    result = DecisionAgent(replace(Settings(), max_model_calls=2), store, lambda _: model).decide(
        "Study or build?"
    )
    assert result.reply.model_dump() == reply.model_dump()
    assert len(model.native_requests) == 1


def test_native_completion_also_preserves_context_phase(store):
    model = NativeCompletionModel(
        [("get_current_time", {})],
        {"kind": "context", "context_summary": "A or B; time unknown."},
    )
    result = DecisionAgent(replace(Settings(), max_model_calls=2), store, lambda _: model).decide(
        "A or B?", phase="review"
    )
    assert result.reply.kind == "context"
    assert model.native_requests[0][0].__name__ == "ReviewReply"


def test_native_completion_shares_timeout(store, reply):
    class SlowNative(NativeCompletionModel):
        async def structured_output(self, *args, **kwargs):
            await asyncio.sleep(1)
            yield {}

    model = SlowNative([("get_current_time", {})], reply.model_dump())
    agent = DecisionAgent(
        replace(Settings(), max_model_calls=2, request_timeout_seconds=0.02), store, lambda _: model
    )
    with pytest.raises(AgentError, match="retry"):
        agent.decide("A or B?")
    assert len(model.requests) == 1


@pytest.mark.parametrize("failure", ["tokens", "structure"])
def test_sdk_completion_exceptions_use_one_native_attempt(store, reply, failure):
    from strands.types.exceptions import MaxTokensReachedException, StructuredOutputException

    class FailedLoop(NativeCompletionModel):
        async def stream(self, *args, **kwargs):
            if failure == "tokens":
                raise MaxTokensReachedException("Token cutoff")
            raise StructuredOutputException("No structured output")
            yield {}

    model = FailedLoop([], reply.model_dump())
    result = DecisionAgent(Settings(), store, lambda _: model).decide("A or B?")
    assert result.reply.kind == "recommendation"
    assert len(model.native_requests) == 1
