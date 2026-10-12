from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from decision_lock.agent import AgentError
from decision_lock.controller import DecisionSession
from decision_lock.models import AgentReply, FinalReply, TurnResult


def turn(reply):
    return TurnResult(reply=reply, provider="Gemini API · test", elapsed_seconds=0)


def test_only_one_clarification_then_lock(store, reply):
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [
        turn(AgentReply(kind="clarification", message="When is your exam?")),
        turn(reply),
    ]
    session.submit("Study or build?", agent)
    assert store.recent() == []
    session.submit("Tomorrow", agent)
    assert agent.decide.call_args.kwargs["clarification"] == "When is your exam?"
    ident = session.lock(store)
    assert session.lock(store) == ident
    assert "Tomorrow" in store.recent()[0]["user_problem"]
    session.feedback(store, True)
    assert store.recent()[0]["helpful"] == 1


def test_failure_preserves_pending_answer_for_retry(reply):
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [
        turn(AgentReply(kind="clarification", message="How much time?")),
        AgentError("Offline"),
        turn(reply),
    ]
    session.submit("Study or build?", agent)
    with pytest.raises(AgentError):
        session.submit("30 minutes", agent)
    assert session.answer == "30 minutes"
    assert session.clarification == "How much time?"
    session.retry(agent)
    assert agent.decide.call_args.kwargs["answer"] == "30 minutes"
    assert session.result.reply == reply


def test_repeated_question_blocked_in_controller():
    agent = Mock()
    agent.decide.return_value = turn(AgentReply(kind="clarification", message="When?"))
    session = DecisionSession()
    session.submit("Study or build?", agent)
    with pytest.raises(AgentError, match="asked again"):
        session.submit("Tomorrow", agent)


def test_final_schema_rejects_second_question():
    with pytest.raises(ValidationError):
        FinalReply(kind="clarification", message="Again?")


def test_no_premature_lock_or_feedback(store):
    session = DecisionSession()
    with pytest.raises(ValueError):
        session.lock(store)
    with pytest.raises(ValueError):
        session.feedback(store, True)


def test_information_is_not_lockable(store):
    session = DecisionSession()
    session.result = turn(AgentReply(kind="information", message="No recent decisions."))
    with pytest.raises(ValueError):
        session.lock(store)
