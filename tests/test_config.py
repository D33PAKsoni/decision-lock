from unittest.mock import patch

import pytest

from decision_lock.config import ConfigurationError, Settings
from decision_lock.providers import create_model, get_api_key


def test_defaults_are_gemini_and_secret_free():
    settings = Settings.from_env({"GEMINI_API_KEY": "private-sentinel"})
    assert settings.model_provider == "gemini"
    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert "private-sentinel" not in repr(settings)


@pytest.mark.parametrize(
    "env",
    [
        {"MODEL_PROVIDER": "bad"},
        {"MODEL_PROVIDER": "bedrock"},
        {"MODEL_PROVIDER": "ollama"},
        {"APP_TIMEZONE": "NoSuch/Zone"},
        {"REQUEST_TIMEOUT_SECONDS": "0"},
        {"REQUEST_TIMEOUT_SECONDS": "601"},
        {"MAX_MODEL_CALLS": "secret-sentinel"},
        {"MAX_MODEL_CALLS": "1"},
        {"GEMINI_MODEL": ""},
        {"GEMINI_MODEL": "x" * 121},
    ],
)
def test_invalid_settings_never_echo_values(env):
    with pytest.raises(ConfigurationError) as caught:
        Settings.from_env(env)
    assert "secret-sentinel" not in str(caught.value)


def test_missing_key_has_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="needs an API key"):
        create_model(Settings())


def test_google_key_alias_and_explicit_key_precedence(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "alias-sentinel")
    assert get_api_key() == "alias-sentinel"
    monkeypatch.setenv("GEMINI_API_KEY", "primary-sentinel")
    assert get_api_key() == "primary-sentinel"


def test_gemini_adapter_uses_supported_sdk_and_bounded_http(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "private-sentinel")
    with patch("strands.models.gemini.GeminiModel") as factory:
        create_model(Settings())
    kwargs = factory.call_args.kwargs
    assert kwargs["client_args"]["api_key"] == "private-sentinel"
    assert kwargs["client_args"]["vertexai"] is False
    assert kwargs["model_id"] == "gemini-3.5-flash-lite"
    assert kwargs["client_args"]["http_options"].timeout == 180000
    assert kwargs["client_args"]["http_options"].retry_options.attempts == 1
    assert kwargs["params"]["max_output_tokens"] == 4096


def test_actual_gemini_adapter_formats_tool_schema(monkeypatch, store):
    from decision_lock.tools import build_tools

    monkeypatch.setenv("GEMINI_API_KEY", "private-sentinel")
    model = create_model(Settings())
    tools = build_tools(store, "Asia/Kolkata", False, [])
    request = model._format_request(
        [{"role": "user", "content": [{"text": "Study or build?"}]}],
        [tool.tool_spec for tool in tools],
        "Be concise.",
        model.get_config()["params"],
    )
    declarations = request["config"]["tools"][0]["function_declarations"]
    assert {d["name"] for d in declarations} == {
        "score_options",
        "get_current_time",
        "get_recent_decisions",
    }
    assert "private-sentinel" not in str(request)


def test_actual_adapter_native_completion_uses_json_schema(monkeypatch, reply):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from decision_lock.models import FinalReply

    monkeypatch.setenv("GEMINI_API_KEY", "private-sentinel")
    model = create_model(Settings())
    generate = AsyncMock(return_value=SimpleNamespace(parsed=reply.model_dump()))
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(model, "_get_client", lambda: client)

    async def invoke():
        return [
            event
            async for event in model.structured_output(
                FinalReply,
                [{"role": "user", "content": [{"text": "Use confirmed context."}]}],
                system_prompt="Keep facts grounded.",
            )
        ]

    events = asyncio.run(invoke())
    assert events[-1]["output"].kind == "recommendation"
    config = generate.call_args.kwargs["config"]
    assert config["response_mime_type"] == "application/json"
    assert config["response_schema"]["properties"]["kind"]["enum"] == [
        "recommendation",
        "information",
        "refusal",
    ]
    assert config["max_output_tokens"] == 4096
    assert "private-sentinel" not in str(generate.call_args)
