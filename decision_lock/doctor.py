"""Local setup check; does not call Gemini or print API keys."""

import sys
from importlib.metadata import version
from pathlib import Path

from dotenv import load_dotenv

from .config import ConfigurationError, Settings
from .providers import create_model


def main() -> int:
    load_dotenv(Path.cwd() / ".env", override=False)
    print(f"Python {sys.version.split()[0]}")
    for name in ("strands-agents", "streamlit", "google-genai"):
        print(f"{name} {version(name)}")
    try:
        settings = Settings.from_env()
        create_model(settings)
    except ConfigurationError as exc:
        print(f"Setup: {exc}")
        return 1
    except Exception:
        print("The Gemini adapter could not be initialized. Check installed dependencies.")
        return 1
    print(f"Provider: {settings.provider_label}")
    print("API key is configured; its value has not been printed.")
    print("No network request was made. Run opted-in live tests to verify API access.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
