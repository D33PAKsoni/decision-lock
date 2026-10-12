"""Validated Gemini settings; API keys are deliberately excluded from this object."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(ValueError):
    """User-correctable setup problem whose message never includes secret values."""


def _integer(env: Mapping[str, str], key: str, default: int, low: int, high: int) -> int:
    try:
        value = int(env.get(key, str(default)))
    except ValueError:
        raise ConfigurationError(f"{key} must be a whole number.") from None
    if not low <= value <= high:
        raise ConfigurationError(f"{key} must be between {low} and {high}.")
    return value


@dataclass(frozen=True)
class Settings:
    model_provider: str = "gemini"
    gemini_model: str = "gemini-3.5-flash-lite"
    timezone: str = "Asia/Kolkata"
    database_path: Path = Path("data/decision_lock.db")
    request_timeout_seconds: int = 180
    max_model_calls: int = 8
    app_mode: str = "local"
    demo_max_requests: int = 50

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        settings = cls(
            model_provider=env.get("MODEL_PROVIDER", "gemini").strip().lower(),
            gemini_model=env.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
            timezone=env.get("APP_TIMEZONE", "Asia/Kolkata").strip(),
            database_path=Path(env.get("DATABASE_PATH", "data/decision_lock.db")),
            request_timeout_seconds=_integer(env, "REQUEST_TIMEOUT_SECONDS", 180, 10, 600),
            max_model_calls=_integer(env, "MAX_MODEL_CALLS", 8, 2, 12),
            app_mode=env.get("APP_MODE", "local").strip().lower(),
            demo_max_requests=_integer(env, "DEMO_MAX_REQUESTS", 50, 1, 500),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.app_mode not in {"local", "public_demo"}:
            raise ConfigurationError("APP_MODE must be local or public_demo.")
        if self.model_provider != "gemini":
            raise ConfigurationError("This version uses Gemini. Set MODEL_PROVIDER=gemini.")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ConfigurationError("APP_TIMEZONE must be a valid IANA timezone.") from None
        if not self.gemini_model or len(self.gemini_model) > 120:
            raise ConfigurationError("GEMINI_MODEL must be a valid non-empty model identifier.")
        if not 10 <= self.request_timeout_seconds <= 600:
            raise ConfigurationError("REQUEST_TIMEOUT_SECONDS must be between 10 and 600.")
        if not 2 <= self.max_model_calls <= 12:
            raise ConfigurationError("MAX_MODEL_CALLS must be between 2 and 12.")

    @property
    def provider_label(self) -> str:
        return f"Gemini API · {self.gemini_model}"
