"""Validated recommendation contract, independent of the presentation layer."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentReply(BaseModel):
    """Context gathering, a reviewed verdict, or a non-lockable explanation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["recommendation", "clarification", "context", "information", "refusal"]
    message: str = Field(default="", max_length=1500, description="Question or explanation")
    recommendation: str = Field(default="", max_length=500, description="One chosen option")
    reasons: list[str] = Field(default_factory=list, max_length=4)
    next_action: str = Field(default="", max_length=500, description="One concrete next move")
    assumptions: list[str] = Field(default_factory=list, max_length=4)
    questions: list[str] = Field(default_factory=list, max_length=4)
    context_summary: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def validate_reply(self) -> Self:
        if self.kind == "recommendation":
            if not self.recommendation or not self.next_action:
                raise ValueError("A recommendation needs a verdict and one concrete next action.")
            if not 2 <= len(self.reasons) <= 4 or any(not r.strip() for r in self.reasons):
                raise ValueError("A recommendation needs 2–4 non-empty short reasons.")
        elif self.kind == "context":
            if (
                not self.context_summary
                or self.questions
                or self.recommendation
                or self.next_action
            ):
                raise ValueError(
                    "Context needs a summary and cannot contain a verdict or questions."
                )
        else:
            if not self.message:
                raise ValueError("A question or explanation needs a message.")
            if self.recommendation or self.next_action:
                raise ValueError("Only a recommendation can offer a lockable decision.")
        if self.kind == "clarification":
            if not self.questions or any(not q.strip() or len(q) > 400 for q in self.questions):
                raise ValueError("Supply 1–4 short, non-empty questions.")
            if len(set(q.casefold() for q in self.questions)) != len(self.questions):
                raise ValueError("Do not repeat a question.")
        elif self.questions:
            raise ValueError("Only clarification replies can contain questions.")
        if any(len(r) > 400 for r in self.reasons + self.assumptions):
            raise ValueError("Keep reasons and assumptions short.")
        return self


class FinalReply(AgentReply):
    """After context review, no further questions are permitted."""

    kind: Literal["recommendation", "information", "refusal"]


class ContextReply(AgentReply):
    """Gather facts or prepare a review, never recommend prematurely."""

    kind: Literal["clarification", "context", "information", "refusal"]


class ReviewReply(ContextReply):
    """At the question limit or after skipping, go directly to review."""

    kind: Literal["context", "information", "refusal"]


class ToolObservation(BaseModel):
    name: str
    result: dict


class TurnResult(BaseModel):
    reply: AgentReply
    tools: list[ToolObservation] = Field(default_factory=list)
    provider: str
    elapsed_seconds: float
