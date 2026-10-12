"""Gemini Developer API adapter. No cloud resource creation or alternate provider."""

import os

from .config import ConfigurationError, Settings


def get_api_key() -> str:
    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not key:
        raise ConfigurationError(
            "Gemini needs an API key. Run the key setup launcher or set GEMINI_API_KEY "
            "privately in your environment."
        )
    return key


def create_model(settings: Settings):
    settings.validate()
    key = get_api_key()
    from google.genai import types
    from strands.models.gemini import GeminiModel

    return GeminiModel(
        client_args={
            "api_key": key,
            "vertexai": False,
            "http_options": types.HttpOptions(
                timeout=settings.request_timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        },
        model_id=settings.gemini_model,
        params={"temperature": 0.2, "max_output_tokens": 4096},
    )
