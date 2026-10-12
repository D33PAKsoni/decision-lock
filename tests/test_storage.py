import pytest

from decision_lock.models import AgentReply
from decision_lock.storage import DecisionStore, StorageError


def test_lock_is_persistent_and_retries_do_not_duplicate(store, reply):
    first = store.lock("token", "Study or build?", reply, "Gemini API · test")
    assert store.lock("token", "Study or build?", reply, "Gemini API · test") == first
    reopened = DecisionStore(store.path)
    reopened.initialize()
    items = reopened.recent()
    assert len(items) == 1 and items[0]["id"] == first
    assert items[0]["next_action"] == reply.next_action


def test_recent_is_newest_first(store, reply):
    ids = [store.lock(str(i), f"Choice {i}", reply, "gemini") for i in range(4)]
    assert [r["id"] for r in store.recent(3)] == list(reversed(ids))[:3]


def test_feedback_targets_correct_decision_and_can_change(store, reply):
    first = store.lock("first", "A", reply, "gemini")
    second = store.lock("second", "B", reply, "gemini")
    store.feedback(first, True)
    store.feedback(first, False)
    by_id = {r["id"]: r for r in store.recent()}
    assert by_id[first]["helpful"] == 0
    assert by_id[second]["helpful"] is None
    with pytest.raises(ValueError):
        store.feedback(999, True)


def test_sql_text_is_data(store, reply):
    text = "'; DROP TABLE decisions; --"
    store.lock(text, text, reply, "gemini")
    assert store.recent()[0]["user_problem"] == text


@pytest.mark.parametrize("limit", [0, 11, True, 1.5, "5"])
def test_history_limits(store, limit):
    with pytest.raises(ValueError):
        store.recent(limit)


def test_non_verdict_cannot_be_saved(store):
    question = AgentReply(kind="clarification", message="When is your exam?")
    with pytest.raises(ValueError):
        store.lock("token", "A", question, "gemini")
    assert store.recent() == []


def test_storage_error_is_sanitized(tmp_path):
    blocker = tmp_path / "private-secret-value"
    blocker.write_text("a file, not a directory")
    with pytest.raises(StorageError) as caught:
        DecisionStore(blocker / "decisions.db").initialize()
    assert "private-secret-value" not in str(caught.value)


def test_feedback_bool_only(store, reply):
    ident = store.lock("token", "A", reply, "gemini")
    with pytest.raises(ValueError):
        store.feedback(ident, "yes")
