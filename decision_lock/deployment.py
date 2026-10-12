"""Public demo isolation and a small process-wide request budget."""

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import MutableMapping

from .config import Settings


def session_settings(settings: Settings, state: MutableMapping) -> Settings:
    if settings.app_mode == "local":
        return settings
    # Keep the TemporaryDirectory owner alive with this browser's Streamlit session.
    # A new decision reuses it; another browser session gets an unrelated random path.
    if "demo_storage" not in state:
        state["demo_storage"] = TemporaryDirectory(prefix="decision-lock-demo-")
    return replace(settings, database_path=Path(state["demo_storage"].name) / "decisions.db")


class DemoBudget:
    """Atomic request reservations shared across sessions in one app process.

    Failed requests count too. This resets on process restart and is not a financial cap.
    One request can produce multiple model/tool turns, each bounded by the agent limits.
    """

    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0
        self._lock = Lock()

    def reserve(self) -> bool:
        with self._lock:
            if self.used >= self.limit:
                return False
            self.used += 1
            return True
