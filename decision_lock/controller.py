"""Bounded context gathering, review, retry preservation and human commitment."""

from uuid import uuid4

from .agent import AgentError, DecisionAgent
from .models import TurnResult
from .storage import DecisionStore


class DecisionSession:
    def __init__(self):
        self.problem = ""
        self.context: list[dict[str, str]] = []
        self.questions: list[str] = []
        self.asked_questions: list[str] = []
        self.stage = "start"
        self.reviewed_context = ""
        self.context_confirmed = False
        self.pending_phase = "gather"
        self.result: TurnResult | None = None
        self.lock_token = str(uuid4())
        self.locked_id: int | None = None
        self.feedback_value: bool | None = None
        self.error = ""
        self.revision = 0

    def submit(self, text: str, agent: DecisionAgent, allow_history: bool = False) -> None:
        if self.stage != "start":
            raise AgentError("Start a new decision to compare another choice.")
        if not text.strip() or len(text) > 4000:
            raise AgentError("Please use 1–4,000 characters.")
        self.problem = text.strip()
        self.pending_phase = "gather"
        self.retry(agent, allow_history)

    def answer_questions(
        self,
        answers: list[str],
        agent: DecisionAgent,
        allow_history: bool = False,
        *,
        skip: bool = False,
    ) -> None:
        if self.stage != "questions" or len(answers) != len(self.questions):
            raise AgentError("Please answer the current questions.")
        if any(len(a) > 1000 for a in answers):
            raise AgentError("Keep each answer under 1,000 characters.")
        # Commit the answers once before the request: retries never append duplicates.
        self.context.extend(
            {"question": question, "answer": answer.strip() or "Not provided"}
            for question, answer in zip(self.questions, answers)
        )
        self.questions = []
        self.stage = "pending"
        self.pending_phase = "review" if skip or len(self.asked_questions) >= 4 else "gather"
        self.retry(agent, allow_history)

    def confirm_context(
        self,
        summary: str,
        agent: DecisionAgent,
        allow_history: bool = False,
    ) -> None:
        if self.stage != "review":
            raise AgentError("Review the context before comparing.")
        if not summary.strip() or len(summary) > 4000:
            raise AgentError("Please use 1–4,000 characters for the context summary.")
        self.reviewed_context = summary.strip()
        self.context_confirmed = True
        self.pending_phase = "recommend"
        self.retry(agent, allow_history)

    def retry(self, agent: DecisionAgent, allow_history: bool = False) -> None:
        self.error = ""
        result = agent.decide(
            self.problem,
            phase=self.pending_phase,
            context=self.context,
            reviewed_context=self.reviewed_context,
            questions_remaining=4 - len(self.asked_questions),
            allow_history=allow_history,
        )
        reply = result.reply
        if self.pending_phase != "recommend":
            if reply.kind == "recommendation":
                raise AgentError("A recommendation arrived before context review. Please retry.")
            if reply.kind == "clarification":
                remaining = 4 - len(self.asked_questions)
                prior = {q.casefold() for q in self.asked_questions}
                if (
                    self.pending_phase == "review"
                    or len(reply.questions) > remaining
                    or any(q.casefold() in prior for q in reply.questions)
                ):
                    raise AgentError("The agent exceeded the question limit. Please retry.")
                self.questions = list(reply.questions)
                self.asked_questions.extend(self.questions)
                self.stage = "questions"
            elif reply.kind == "context":
                self.reviewed_context = reply.context_summary
                self.context_confirmed = False
                self.stage = "review"
            else:
                self.stage = "finished"
        else:
            if reply.kind not in {"recommendation", "information", "refusal"}:
                raise AgentError("The agent did not finish the comparison. Please retry.")
            self.stage = "finished"
        self.result = result
        self.revision += 1

    def lock(self, store: DecisionStore) -> int:
        if self.locked_id is not None:
            return self.locked_id
        if (
            not self.context_confirmed
            or not self.result
            or self.result.reply.kind != "recommendation"
        ):
            raise ValueError("Review the context and get a recommendation before locking.")
        problem = self.problem + "\n\nConfirmed context:\n" + self.reviewed_context
        for entry in self.context:
            problem += f"\nQuestion: {entry['question']}\nAnswer: {entry['answer']}"
        self.locked_id = store.lock(
            self.lock_token, problem, self.result.reply, self.result.provider
        )
        return self.locked_id

    def feedback(self, store: DecisionStore, helpful: bool) -> None:
        if self.locked_id is None:
            raise ValueError("Lock the decision before giving feedback.")
        store.feedback(self.locked_id, helpful)
        self.feedback_value = helpful
