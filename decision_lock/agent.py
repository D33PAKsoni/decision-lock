"""A genuine Strands loop; a fresh agent isolates each turn and each retry."""

import asyncio
import json
import logging
from time import perf_counter
from typing import Callable

from strands import Agent
from strands.types.exceptions import MaxTokensReachedException, StructuredOutputException

from .config import ConfigurationError, Settings
from .models import ContextReply, FinalReply, ReviewReply, TurnResult
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
        phase: str = "recommend",
        context: list[dict[str, str]] | None = None,
        reviewed_context: str = "",
        questions_remaining: int = 4,
    ) -> TurnResult:
        if not problem.strip() or len(problem) > 4000 or len(answer) > 4000:
            raise AgentError(
                "Please enter a decision and keep each message under 4,000 characters."
            )
        quiet_dependency_logs()
        started = perf_counter()
        observations = []
        if phase not in {"gather", "review", "recommend"}:
            raise AgentError("Unknown decision stage.")
        if len(reviewed_context) > 4000:
            raise AgentError("Keep the context summary under 4,000 characters.")
        schema = (
            (ContextReply if questions_remaining > 0 else ReviewReply)
            if phase == "gather"
            else (ReviewReply if phase == "review" else FinalReply)
        )
        request = json.dumps(
            {
                "decision": problem,
                "clarification_already_asked": clarification,
                "answer": answer,
                "allow_history": allow_history,
                "phase": phase,
                "context_answers": context or [],
                "reviewed_context": reviewed_context,
                "questions_remaining": questions_remaining,
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

            async def complete():
                stop_reason = "missing_output"
                try:
                    result = await agent.invoke_async(
                        request,
                        structured_output_model=schema,
                        structured_output_prompt=(
                            f"Finish this {phase} stage by calling {schema.__name__}. "
                            "Supply short values that satisfy its schema. For a recommendation, "
                            "include one chosen option, 2–4 reasons and one concrete next_action. "
                            "Do not call another decision tool now."
                        ),
                        # Reserve one model call for a native JSON completion if necessary.
                        limits={"turns": self.settings.max_model_calls - 1, "output_tokens": 8192},
                    )
                    if result.structured_output is not None:
                        return schema.model_validate(result.structured_output.model_dump())
                    stop_reason = str(result.stop_reason)
                    if stop_reason not in {"limit_turns", "limit_output_tokens", "end_turn"}:
                        raise AgentError(
                            "Gemini stopped without a complete response. "
                            "Your context is preserved. "
                            "Please retry or check the model settings."
                        )
                except (MaxTokensReachedException, StructuredOutputException) as exc:
                    stop_reason = type(exc).__name__
                LOGGER.warning("Completing model response (phase=%s, stop=%s).", phase, stop_reason)
                completion = json.dumps(
                    {
                        "request": json.loads(request),
                        "executed_tools": [item.model_dump() for item in observations],
                        "instruction": (
                            "Finish the requested phase now using only the confirmed context and "
                            "actual tool results. Do not request more tools. Missing facts remain "
                            "unknown. Return a concise response matching the supplied schema. "
                            "For recommend, give a recommendation with 2–4 reasons "
                            "and a next_action when the context supports it; otherwise "
                            "explain what prevents a choice."
                        ),
                    }
                )
                # Adapter-level structured_output uses Gemini's native response schema.
                # No deprecated Agent.structured_output API, invented verdict or unbounded retry.
                messages = [{"role": "user", "content": [{"text": completion}]}]
                async for event in model.structured_output(
                    schema, messages, system_prompt=SYSTEM_PROMPT
                ):
                    if event.get("output") is not None:
                        return schema.model_validate(event["output"].model_dump())
                raise AgentError(
                    "Gemini could not complete this response. Your context is preserved. "
                    "Please retry or check the model settings."
                )

            async def invoke():
                # Tool reasoning and native completion share one overall deadline.
                return await asyncio.wait_for(
                    complete(), timeout=self.settings.request_timeout_seconds
                )

            reply = asyncio.run(invoke())
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
