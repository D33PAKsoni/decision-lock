from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from decision_lock.agent import AgentError, DecisionAgent
from decision_lock.models import AgentReply, TurnResult
from decision_lock.storage import DecisionStore, StorageError

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("APP_MODE", "local")
    monkeypatch.delenv("DECISION_LOCK_PUBLIC_ENTRY", raising=False)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    return AppTest.from_file(str(APP), default_timeout=15)


def button(app, label):
    return next(b for b in app.button if b.label == label)


def fake_result(reply):
    return TurnResult(reply=reply, provider="Gemini API · test fixture", elapsed_seconds=0)


def test_first_run_no_model_needed(app):
    app.run()
    assert not app.exception
    assert app.title[0].value == "Decision Lock"
    assert any(b.label == "📚 Study or build?" for b in app.button)


def contextual_result(reply):
    def decide(*a, **kw):
        if kw.get("phase") == "recommend":
            return fake_result(reply)
        return fake_result(
            AgentReply(kind="context", context_summary="A or B? Priority: getting it working.")
        )

    return decide


def compare(app):
    button(app, "Confirm context & compare").click().run()


def test_verdict_lock_feedback_persist_and_reset(app, monkeypatch, reply):
    monkeypatch.setattr(DecisionAgent, "decide", contextual_result(reply))
    app.run()
    app.chat_input[0].set_value("Study or build?").run()
    compare(app)
    assert not app.exception
    assert any(s.value == reply.recommendation for s in app.subheader)
    button(app, "🔒 Lock This Decision").click().run()
    assert not app.exception
    assert any("Decision locked" in s.value for s in app.success)
    button(app, "👍 Yes").click().run()
    session = app.session_state["decision"]
    store = DecisionStore(app.session_state["settings"].database_path)
    assert store.recent()[0]["helpful"] == 1
    assert session.locked_id is not None
    button(app, "＋ New decision").click().run()
    assert app.session_state["decision"].problem == ""
    assert len(store.recent()) == 1


def test_provider_failure_friendly_then_retry(app, monkeypatch, reply):
    def fail(*a, **kw):
        raise AgentError("Model offline. Your input is preserved.")

    monkeypatch.setattr(DecisionAgent, "decide", fail)
    app.run()
    app.chat_input[0].set_value("A or B?").run()
    assert not app.exception
    assert any("Model offline" in e.value for e in app.error)
    assert app.session_state["decision"].problem == "A or B?"
    monkeypatch.setattr(DecisionAgent, "decide", contextual_result(reply))
    button(app, "↻ Retry this decision").click().run()
    assert app.session_state["decision"].stage == "review"
    compare(app)
    assert app.session_state["decision"].result.reply == reply
    assert not app.exception


def test_context_questions_review_correction_and_lock(app, monkeypatch, reply):
    replies = iter(
        [
            AgentReply(
                kind="clarification",
                message="Two things first.",
                questions=["When is the exam?", "How much time?"],
            ),
            AgentReply(kind="context", context_summary="Exam tomorrow; 30 minutes."),
            reply,
        ]
    )
    calls = []

    def decide(*a, **kw):
        calls.append(kw)
        return fake_result(next(replies))

    monkeypatch.setattr(DecisionAgent, "decide", decide)
    app.run()
    app.chat_input[0].set_value("Study or build?").run()
    assert not any(b.label == "🔒 Lock This Decision" for b in app.button)
    next(x for x in app.text_input if x.label == "When is the exam?").set_value("Tomorrow")
    next(x for x in app.text_input if x.label == "How much time?").set_value("30 minutes")
    button(app, "Continue with these answers").click().run()
    assert not app.exception
    assert not any(b.label == "🔒 Lock This Decision" for b in app.button)
    app.text_area[0].set_value("Exam next week; project due tonight. 30 minutes.")
    compare(app)
    assert calls[-1]["reviewed_context"].startswith("Exam next week")
    assert any(b.label == "🔒 Lock This Decision" for b in app.button)
    button(app, "🔒 Lock This Decision").click().run()
    assert not app.exception
    assert app.session_state["decision"].context_confirmed


def test_skip_questions_goes_to_review(app, monkeypatch):
    calls = []

    def decide(*a, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return fake_result(
                AgentReply(
                    kind="clarification", message="Context first.", questions=["When?", "Time?"]
                )
            )
        return fake_result(
            AgentReply(kind="context", context_summary="A or B; deadline and time unknown.")
        )

    monkeypatch.setattr(DecisionAgent, "decide", decide)
    app.run()
    app.chat_input[0].set_value("A or B?").run()
    button(app, "That’s enough — review now").click().run()
    assert not app.exception
    assert calls[-1]["phase"] == "review"
    assert app.session_state["decision"].stage == "review"


def test_lock_failure_keeps_verdict_visible(app, monkeypatch, reply):
    monkeypatch.setattr(DecisionAgent, "decide", contextual_result(reply))

    def fail(*a, **kw):
        raise StorageError("Disk unavailable")

    app.run()
    app.chat_input[0].set_value("A or B?").run()
    compare(app)
    monkeypatch.setattr(DecisionStore, "lock", fail)
    button(app, "🔒 Lock This Decision").click().run()
    assert not app.exception
    assert any("couldn’t save the lock" in e.value for e in app.error)
    assert app.session_state["decision"].locked_id is None
    assert any(s.value == reply.recommendation for s in app.subheader)


def test_invalid_model_change_keeps_current_configuration(app):
    app.run()
    app.text_input[0].set_value("")
    button(app, "Apply settings").click().run()
    assert app.session_state["settings"].gemini_model == "gemini-3.5-flash-lite"
    assert any("GEMINI_MODEL" in e.value for e in app.error)
    assert not app.exception


def test_model_change_starts_a_fresh_decision(app):
    app.run()
    app.text_input[0].set_value("gemini-3.1-flash-lite")
    button(app, "Apply settings").click().run()
    assert app.session_state["settings"].gemini_model == "gemini-3.1-flash-lite"
    assert app.session_state["decision"].problem == ""
    assert not app.exception


def test_public_demo_has_isolated_storage_and_no_model_selector(app, monkeypatch, reply):
    monkeypatch.setenv("APP_MODE", "public_demo")
    monkeypatch.setattr(DecisionAgent, "decide", contextual_result(reply))
    second = AppTest.from_file(str(APP), default_timeout=15)
    app.run()
    second.run()
    assert not app.exception and not second.exception
    first_path = app.session_state["settings"].database_path
    second_path = second.session_state["settings"].database_path
    assert first_path != second_path
    assert len(app.text_input) == 0
    app.chat_input[0].set_value("Private first-session choice").run()
    compare(app)
    button(app, "🔒 Lock This Decision").click().run()
    assert len(DecisionStore(first_path).recent()) == 1
    assert DecisionStore(second_path).recent() == []
    button(app, "＋ New decision").click().run()
    assert app.session_state["settings"].database_path == first_path


def test_cloud_entry_forces_public_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "local")
    monkeypatch.setenv("DECISION_LOCK_PUBLIC_ENTRY", "")
    cloud = AppTest.from_file(str(APP.with_name("streamlit_app.py")), default_timeout=15)
    cloud.run()
    assert not cloud.exception
    assert cloud.session_state["settings"].app_mode == "public_demo"
    assert len(cloud.text_input) == 0
