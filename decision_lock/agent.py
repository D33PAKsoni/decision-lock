"""A genuine Strands loop; a fresh agent isolates each turn and each retry."""

import asyncio
import json
import logging
from time import perf_counter
from typing import Callable

from strands import Agent

from .config import ConfigurationError, Settings
from .models import AgentReply, FinalReply, TurnResult
from .prompts import SYSTEM_PROMPT
from .providers import create_model
from .storage import DecisionStore
from .tools import build_tools

LOGGER = logging.getLogger("decision_lock")
MODEL_ERROR = (
    "I couldn’t reach a usable model response just now. Your decision is still here — "
    "check the model connection and retry."
)


class AgentError(RuntimeError):
    """A safe error ready to show in the UI."""


def quiet_dependency_logs() -> None:
    # SDK error traces can include prompts, request headers or provider exception messages.
    # Normal app logs expose only the exception class, never those payloads.
    for name in ("strands", "httpx", "httpcore", "httpx2", "google.genai", "boto3", "botocore"):
        logging.getLogger(name).setLevel(logging.CRITICAL + 1)


class DecisionAgent:
    def __init__(
        self, settings: Settings, store: DecisionStore, model_factory: Callable = create_model
    ):
        self.settings = settings
        self.store = store
        self.model_factory = model_factory

    def decide(
        self,
        problem: str,
        *,
        clarification: str = "",
        answer: str = "",
        allow_history: bool = False,
    ) -> TurnResult:
        if not problem.strip() or len(problem) > 4000 or len(answer) > 4000:
            raise AgentError(
                "Please enter a decision and keep each message under 4,000 characters."
            )
        quiet_dependency_logs()
        started = perf_counter()
        observations = []
        schema = FinalReply if clarification else AgentReply
        request = json.dumps(
            {
                "decision": problem,
                "clarification_already_asked": clarification,
                "answer": answer,
                "allow_history": allow_history,
            }
        )
        try:
            model = self.model_factory(self.settings)
            agent = Agent(
                model=model,
                tools=build_tools(self.store, self.settings.timezone, allow_history, observations),
                system_prompt=SYSTEM_PROMPT,
                callback_handler=None,
                retry_strategy=None,
            )

            async def invoke():
                return await asyncio.wait_for(
                    agent.invoke_async(
                        request,
                        structured_output_model=schema,
                        limits={"turns": self.settings.max_model_calls, "output_tokens": 6000},
                    ),
                    timeout=self.settings.request_timeout_seconds,
                )

            result = asyncio.run(invoke())
            if result.structured_output is None:
                raise AgentError("The model could not finish a clear verdict. Please retry.")
            reply = schema.model_validate(result.structured_output.model_dump())
        except ConfigurationError:
            raise
        except AgentError:
            raise
        except Exception as exc:
            LOGGER.warning("Model request failed (%s).", type(exc).__name__)
            code = getattr(exc, "code", None)
            if code == 429:
                raise AgentError(
                    "Gemini’s quota is temporarily exhausted. Your input is saved here — "
                    "check your API limits or retry later."
                ) from None
            if code in {400, 401, 403}:
                raise AgentError(
                    "Gemini rejected the request. Check your API key, permissions and model "
                    "settings. Your input is preserved."
                ) from None
            if code == 404:
                raise AgentError(
                    "The Gemini model is unavailable. Check the model setting."
                ) from None
            raise AgentError(MODEL_ERROR) from None
        return TurnResult(
            reply=reply,
            tools=observations,
            provider=self.settings.provider_label,
            elapsed_seconds=round(perf_counter() - started, 3),
        )
