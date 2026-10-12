"""A deterministic SDK protocol fixture, never a substitute for a real-model demo."""

import copy
import json

from strands.models.model import Model


class ScriptedModel(Model):
    def __init__(self, actions: list[tuple[str, dict]]):
        self.actions = list(actions)
        self.requests = []
        self.config = {"model_id": "scripted-test-only"}

    def update_config(self, **model_config):
        self.config.update(model_config)

    def get_config(self):
        return self.config

    async def structured_output(self, output_model, prompt, **kwargs):
        raise AssertionError("Use the current structured_output_model agent interface.")
        yield  # This abstract API is an async generator, even when unused.

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.requests.append(copy.deepcopy(messages))
        if not self.actions:
            raise AssertionError("Unexpected extra model call.")
        name, arguments = self.actions.pop(0)
        assert name in {spec["name"] for spec in tool_specs}
        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "start": {
                    "toolUse": {"name": name, "toolUseId": f"fixture-{len(self.requests)}"},
                }
            }
        }
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 20, "outputTokens": 20, "totalTokens": 40},
                "metrics": {"latencyMs": 0},
            }
        }
