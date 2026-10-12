from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from decision_lock.agent import AgentError
from decision_lock.controller import DecisionSession
from decision_lock.models import AgentReply, ContextReply, FinalReply, ReviewReply, TurnResult


def turn(reply):
    return TurnResult(reply=reply, provider="Gemini API · test", elapsed_seconds=0)


def questions(*items):
    return ContextReply(
        kind="clarification", message="A little context first.", questions=list(items)
    )


def review():
    return ContextReply(
        kind="context", context_summary="Study or build. Exam tomorrow; 30 minutes."
    )


def test_context_review_then_human_lock(store, reply):
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [
        turn(questions("When is the exam?", "How much time?")),
        turn(review()),
        turn(reply),
    ]
    session.submit("Study or build?", agent)
    with pytest.raises(ValueError):
        session.lock(store)
    session.answer_questions(["Tomorrow", "30 minutes"], agent)
    assert session.stage == "review"
    assert store.recent() == []
    with pytest.raises(ValueError):
        session.lock(store)
    session.confirm_context("Exam next week, not tomorrow. 30 minutes; project due tonight.", agent)
    assert agent.decide.call_args.kwargs["reviewed_context"].startswith("Exam next week")
    assert agent.decide.call_args.kwargs["phase"] == "recommend"
    ident = session.lock(store)
    assert session.lock(store) == ident
    assert "Exam next week" in store.recent()[0]["user_problem"]
    assert "30 minutes" in store.recent()[0]["user_problem"]
    session.feedback(store, True)
    assert store.recent()[0]["helpful"] == 1


def test_retry_preserves_answers_without_duplicates():
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [
        turn(questions("When?", "Time?")),
        AgentError("Offline"),
        turn(review()),
    ]
    session.submit("Study or build?", agent)
    with pytest.raises(AgentError):
        session.answer_questions(["Tomorrow", "30 minutes"], agent)
    assert len(session.context) == 2
    session.retry(agent)
    assert len(session.context) == 2
    assert session.stage == "review"
    assert agent.decide.call_args.kwargs["context"][0]["answer"] == "Tomorrow"


def test_adaptive_followup_and_four_question_limit():
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [
        turn(questions("When?", "Time?")),
        turn(questions("Priority?", "Energy?")),
        turn(review()),
    ]
    session.submit("A or B?", agent)
    session.answer_questions(["Tomorrow", "30 minutes"], agent)
    assert agent.decide.call_args.kwargs["questions_remaining"] == 2
    session.answer_questions(["Passing", "Low"], agent)
    assert agent.decide.call_args.kwargs["phase"] == "review"
    assert len(session.asked_questions) == 4


def test_skip_preserves_partial_answers_and_forces_review():
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [turn(questions("When?", "Time?")), turn(review())]
    session.submit("A or B?", agent)
    session.answer_questions(["Tomorrow", ""], agent, skip=True)
    assert session.context[1]["answer"] == "Not provided"
    assert agent.decide.call_args.kwargs["phase"] == "review"


def test_premature_recommendation_rejected(reply):
    session = DecisionSession()
    agent = Mock()
    agent.decide.return_value = turn(reply)
    with pytest.raises(AgentError, match="before context review"):
        session.submit("A or B?", agent)
    assert not session.context_confirmed


def test_repeated_and_excess_questions_rejected():
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [turn(questions("When?", "Time?")), turn(questions("When?"))]
    session.submit("A or B?", agent)
    with pytest.raises(AgentError, match="question limit"):
        session.answer_questions(["Tomorrow", "30 minutes"], agent)
    assert len(session.asked_questions) == 2


def test_schema_phase_boundaries():
    with pytest.raises(ValidationError):
        FinalReply(kind="clarification", message="Again?", questions=["When?"])
    with pytest.raises(ValidationError):
        ReviewReply(kind="clarification", message="Again?", questions=["When?"])
    with pytest.raises(ValidationError):
        ContextReply(
            kind="recommendation", recommendation="A", reasons=["x", "y"], next_action="Go"
        )
    with pytest.raises(ValidationError):
        questions("When?", "When?")


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


def test_followup_cannot_exceed_remaining_budget():
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [
        turn(questions("When?", "Time?", "Priority?")),
        turn(questions("Energy?", "Budget?")),
    ]
    session.submit("A or B?", agent)
    with pytest.raises(AgentError, match="question limit"):
        session.answer_questions(["Tomorrow", "30 minutes", "Finish"], agent)
    assert len(session.asked_questions) == 3


def test_failed_comparison_retries_corrected_context(store, reply):
    session = DecisionSession()
    agent = Mock()
    agent.decide.side_effect = [turn(review()), AgentError("Offline"), turn(reply)]
    session.submit("Study or build?", agent)
    with pytest.raises(AgentError):
        session.confirm_context("Actually the exam is next week.", agent)
    with pytest.raises(ValueError):
        session.lock(store)
    session.retry(agent)
    assert agent.decide.call_args.kwargs["reviewed_context"] == "Actually the exam is next week."
    assert agent.decide.call_args.kwargs["phase"] == "recommend"
    assert session.lock(store) > 0
