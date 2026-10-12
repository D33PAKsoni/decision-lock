import pytest

from decision_lock.models import AgentReply
from decision_lock.storage import DecisionStore


@pytest.fixture
def reply():
    return AgentReply(
        kind="recommendation",
        recommendation="Study AWS for 30 minutes",
        reasons=["Your exam is tomorrow.", "A short session fits the time available."],
        next_action="Open one practice module and set a 30-minute timer.",
    )


@pytest.fixture
def store(tmp_path):
    storage = DecisionStore(tmp_path / "data" / "decisions.db")
    storage.initialize()
    return storage
