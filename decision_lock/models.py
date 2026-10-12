"""Validated recommendation contract, independent of the presentation layer."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentReply(BaseModel):
    """Either one clarification, a lockable verdict, or a non-lockable explanation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["recommendation", "clarification", "information", "refusal"]
    message: str = Field(default="", max_length=1500, description="Question or explanation")
    recommendation: str = Field(default="", max_length=500, description="One chosen option")
    reasons: list[str] = Field(default_factory=list, max_length=4)
    next_action: str = Field(default="", max_length=500, description="One concrete next move")
    assumptions: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_reply(self) -> Self:
        if self.kind == "recommendation":
            if not self.recommendation or not self.next_action:
                raise ValueError("A recommendation needs a verdict and one concrete next action.")
            if not 2 <= len(self.reasons) <= 4 or any(not r.strip() for r in self.reasons):
                raise ValueError("A recommendation needs 2–4 non-empty short reasons.")
        else:
            if not self.message:
                raise ValueError("A question or explanation needs a message.")
            if self.recommendation or self.next_action:
                raise ValueError("Only a recommendation can offer a lockable decision.")
        if any(len(r) > 400 for r in self.reasons + self.assumptions):
            raise ValueError("Keep reasons and assumptions short.")
        return self


class FinalReply(AgentReply):
    """After the one clarification, the schema cannot request another question."""

    kind: Literal["recommendation", "information", "refusal"]


class ToolObservation(BaseModel):
    name: str
    result: dict


class TurnResult(BaseModel):
    reply: AgentReply
    tools: list[ToolObservation] = Field(default_factory=list)
    provider: str
    elapsed_seconds: float
