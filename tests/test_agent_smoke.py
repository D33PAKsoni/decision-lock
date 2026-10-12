"""Explicitly opted-in real-model tests. These are not mocked."""

import os

import pytest
from dotenv import load_dotenv

from decision_lock.agent import DecisionAgent
from decision_lock.config import Settings

load_dotenv(override=False)


@pytest.fixture
def live_settings():
    if os.environ.get("RUN_LIVE_TESTS", "false").lower() != "true":
        pytest.skip("Set RUN_LIVE_TESTS=true to enable real model calls.")
    settings = Settings.from_env()
    from decision_lock.config import ConfigurationError
    from decision_lock.providers import get_api_key

    try:
        get_api_key()
    except ConfigurationError:
        pytest.skip("Gemini API key is not configured.")
    return settings


@pytest.mark.integration
def test_live_recommendation_lock_feedback(live_settings, store):
    result = DecisionAgent(live_settings, store).decide(
        "I have 30 minutes. My AWS exam is tomorrow. My side project has no deadline. "
        "Should I study or work on the project? Passing the exam is my priority."
    )
    assert result.reply.kind == "recommendation"
    ident = store.lock("live-smoke", "Study or build?", result.reply, result.provider)
    store.feedback(ident, True)
    assert store.recent()[0]["helpful"] == 1


@pytest.mark.integration
def test_live_model_selects_scoring_tool(live_settings, store):
    result = DecisionAgent(live_settings, store).decide(
        "Please compare Study AWS and Build side project using score_options. "
        "My scores (0–10, higher is better) are: Study AWS urgency 9, importance 8, "
        "effort_fit 8, reversibility 7; Build side project urgency 5, importance 7, "
        "effort_fit 6, reversibility 8. My weights are urgency 0.4, importance 0.3, "
        "effort_fit 0.2, reversibility 0.1. I have 30 minutes. Give one next action."
    )
    assert result.reply.kind == "recommendation"
    assert any(t.name == "score_options" and t.result.get("status") == "ok" for t in result.tools)
