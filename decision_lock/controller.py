"""Conversation state, retry preservation and human commitment, without UI code."""

from uuid import uuid4

from .agent import AgentError, DecisionAgent
from .models import TurnResult
from .storage import DecisionStore


class DecisionSession:
    def __init__(self):
        self.problem = ""
        self.clarification = ""
        self.answer = ""
        self.result: TurnResult | None = None
        self.lock_token = str(uuid4())
        self.locked_id: int | None = None
        self.feedback_value: bool | None = None
        self.error = ""

    def submit(self, text: str, agent: DecisionAgent, allow_history: bool = False) -> None:
        if not text.strip() or len(text) > 4000:
            raise AgentError("Please use 1–4,000 characters.")
        if self.result and self.result.reply.kind != "clarification":
            raise AgentError("Start a new decision to compare another choice.")
        if self.clarification:
            self.answer = text.strip()
        else:
            self.problem = text.strip()
        self.retry(agent, allow_history)

    def retry(self, agent: DecisionAgent, allow_history: bool = False) -> None:
        # Do not count a failed attempt as a clarification or discard user input.
        self.error = ""
        result = agent.decide(
            self.problem,
            clarification=self.clarification,
            answer=self.answer,
            allow_history=allow_history,
        )
        if self.clarification and result.reply.kind == "clarification":
            raise AgentError("The model asked again instead of finishing. Please retry.")
        self.result = result
        if result.reply.kind == "clarification":
            self.clarification = result.reply.message

    def lock(self, store: DecisionStore) -> int:
        if self.locked_id is not None:
            return self.locked_id
        if not self.result or self.result.reply.kind != "recommendation":
            raise ValueError("There is no completed recommendation to lock.")
        problem = self.problem
        if self.answer:
            problem += f"\nClarification: {self.clarification}\nAnswer: {self.answer}"
        self.locked_id = store.lock(
            self.lock_token, problem, self.result.reply, self.result.provider
        )
        return self.locked_id

    def feedback(self, store: DecisionStore, helpful: bool) -> None:
        if self.locked_id is None:
            raise ValueError("Lock the decision before giving feedback.")
        store.feedback(self.locked_id, helpful)
        self.feedback_value = helpful
