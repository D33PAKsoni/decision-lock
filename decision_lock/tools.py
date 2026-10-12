"""Bind read-only tools to one request and record actual executions for the UI."""

from datetime import datetime
from zoneinfo import ZoneInfo

from strands import tool

from .models import ToolObservation
from .scoring import score_options as calculate_scores
from .storage import DecisionStore, StorageError


def build_tools(
    store: DecisionStore, timezone: str, allow_history: bool, observations: list[ToolObservation]
) -> list:
    def observe(name: str, result: dict) -> dict:
        observations.append(ToolObservation(name=name, result=result))
        return result

    @tool
    def score_options(options: list[dict], weights: dict[str, float]) -> dict:
        """Rank 2–5 options using 1–6 weighted criteria and explicit 0–10 scores.

        Higher scores mean a better fit (use effort_fit, not raw cost/effort).
        Never fill in missing scores. Weights normalize automatically; ties are explicit.

        Args:
            options: Objects with name and scores, e.g. {"name":"Study","scores":{"fit":8}}.
            weights: Nonnegative criterion weights, e.g. {"fit":1}.
        """
        return observe("score_options", calculate_scores(options, weights))

    @tool
    def get_current_time() -> dict:
        """Get the current local ISO-8601 time and timezone to interpret tonight or tomorrow."""
        return observe(
            "get_current_time",
            {
                "status": "ok",
                "datetime": datetime.now(ZoneInfo(timezone)).isoformat(),
                "timezone": timezone,
            },
        )

    @tool
    def get_recent_decisions(limit: int = 5) -> dict:
        """Recall up to 10 human-locked decisions, only with explicit history permission.

        Args:
            limit: Number of recent locked decisions; integer 1–10.
        """
        if not allow_history:
            return observe(
                "get_recent_decisions",
                {
                    "status": "permission_required",
                    "message": (
                        "History is private. Ask the user to enable Use my locked decisions."
                    ),
                },
            )
        try:
            result = {"status": "ok", "decisions": store.recent(limit)}
        except ValueError:
            result = {"status": "invalid_input", "message": "History limit must be 1–10."}
        except StorageError:
            result = {"status": "unavailable", "message": "Local decision history is unavailable."}
        return observe("get_recent_decisions", result)

    return [score_options, get_current_time, get_recent_decisions]
