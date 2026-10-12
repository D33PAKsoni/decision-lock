"""Local Streamlit entry point. Run with: streamlit run app.py."""

import os
from dataclasses import replace
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from decision_lock.agent import AgentError, DecisionAgent
from decision_lock.config import ConfigurationError, Settings
from decision_lock.controller import DecisionSession
from decision_lock.deployment import DemoBudget, session_settings
from decision_lock.storage import DecisionStore, StorageError

st.set_page_config(page_title="Decision Lock", page_icon="🔒", layout="centered")
# Reading root-level Streamlit secrets also supports Community Cloud configuration.
try:
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_MODEL",
        "MODEL_PROVIDER",
        "APP_MODE",
        "APP_TIMEZONE",
        "DEMO_MAX_REQUESTS",
        "REQUEST_TIMEOUT_SECONDS",
        "MAX_MODEL_CALLS",
    ):
        if name in st.secrets:
            os.environ.setdefault(name, str(st.secrets[name]))
except FileNotFoundError:
    pass
load_dotenv(Path(__file__).parent / ".env", override=False)
if os.environ.get("DECISION_LOCK_PUBLIC_ENTRY") == "1":
    os.environ["APP_MODE"] = "public_demo"

st.html("""
<style>
  .stMainBlockContainer {max-width: 880px; padding-top: 3rem; padding-bottom: 3rem;}
  h1 {letter-spacing: -0.045em; font-size: 3.4rem !important;}
  h2, h3 {letter-spacing: -0.02em;}
  .eyebrow {color: #23634A; font: 600 12px/1.5 sans-serif; letter-spacing: .16em;}
  .stButton button {border-radius: 12px; min-height: 44px;}
  @media (max-width: 600px) {h1 {font-size: 2.6rem !important;}}
</style>
""")

if "settings" not in st.session_state:
    try:
        st.session_state.settings = session_settings(Settings.from_env(), st.session_state)
    except ConfigurationError as exc:
        st.error(str(exc))
        st.info("Check your environment settings, then refresh. Start with .env.example.")
        st.stop()
if "decision" not in st.session_state:
    st.session_state.decision = DecisionSession()

settings: Settings = st.session_state.settings
session: DecisionSession = st.session_state.decision
store = DecisionStore(settings.database_path)
storage_available = True
try:
    store.initialize()
except StorageError:
    storage_available = False
agent = DecisionAgent(settings, store)


def new_decision():
    st.session_state.decision = DecisionSession()
    st.session_state.allow_history = False


def run_turn(text: str | None = None):
    if settings.app_mode == "public_demo":
        if not demo_budget(settings.demo_max_requests).reserve():
            session.error = "This demo has reached its request limit. Please try again later."
            st.rerun()
    try:
        with st.spinner("Weighing the options. Let’s find your next move…"):
            if text is None:
                session.retry(agent, st.session_state.get("allow_history", False))
            else:
                session.submit(text, agent, st.session_state.get("allow_history", False))
    except (AgentError, ConfigurationError) as exc:
        session.error = str(exc)
    st.rerun()


@st.cache_resource
def demo_budget(limit: int) -> DemoBudget:
    return DemoBudget(limit)


with st.sidebar:
    st.markdown("### 🔒 Decision Lock")
    st.caption("A little clarity. One next move.")
    st.button("＋ New decision", on_click=new_decision, use_container_width=True)
    st.divider()
    st.markdown("**Your locked decisions**")
    st.caption(
        "Temporary history for this browser session."
        if settings.app_mode == "public_demo"
        else "Saved on this computer only."
    )
    if storage_available:
        try:
            recent = store.recent()
            if not recent:
                st.caption("Your first lock will appear here.")
            for item in recent:
                with st.expander(f"🔒 {item['recommendation']}"):
                    st.write(item["next_action"])
                    st.caption(item["created_at"][:16].replace("T", " ") + " UTC")
                    st.caption(item["provider"])
                    if item["helpful"] is not None:
                        st.caption("Feedback: 👍 Useful" if item["helpful"] else "Feedback: 👎")
        except StorageError:
            st.caption("History is temporarily unavailable.")
    else:
        st.caption("History is temporarily unavailable.")
    if settings.app_mode == "local":
        with st.expander("Model settings"):
            st.caption("Applying a model change starts a new decision.")
            with st.form("model_settings"):
                model_name = st.text_input("Gemini model", settings.gemini_model)
                applied = st.form_submit_button("Apply settings")
            if applied:
                try:
                    updated = replace(settings, gemini_model=model_name.strip())
                    updated.validate()
                    st.session_state.settings = updated
                    new_decision()
                    st.rerun()
                except ConfigurationError as exc:
                    st.error(str(exc))
            st.caption(
                "API credentials are configured privately through the launcher or environment."
            )

st.html('<div class="eyebrow">LESS OVERTHINKING. MORE DOING.</div>')
st.title("Decision Lock")
st.markdown(
    "Tell me the small decision you’re overthinking. I’ll help you choose and turn it "
    "into **one next action**."
)
st.caption(settings.provider_label)
if settings.app_mode == "public_demo":
    st.caption(
        "Public demo · Your history is separate from other visitors and may reset. "
        "Download your next action to keep it."
    )
if not storage_available:
    st.warning("Local saving is unavailable. You can still get and copy a recommendation.")

if not session.problem:
    st.divider()
    st.markdown("**Start with a choice you’re sitting on**")
    examples = [
        ("📚 Study or build?", "Should I study for my AWS exam or work on my side project?"),
        ("🏃 Gym or assignment?", "Should I go to the gym tonight or finish my assignment?"),
        (
            "⏱️ Only 30 minutes",
            "I have 30 minutes. Should I fix a bug blocking my project "
            "or polish its colors? Getting it working is my priority.",
        ),
    ]
    for column, (label, prompt) in zip(st.columns(3), examples):
        if column.button(label, use_container_width=True):
            run_turn(prompt)
    st.caption(
        "Small, practical choices work best: study, projects, plans and everyday priorities."
    )
else:
    with st.chat_message("user"):
        st.write(session.problem)
    if session.clarification:
        with st.chat_message("assistant"):
            st.write(session.clarification)
        if session.answer:
            with st.chat_message("user"):
                st.write(session.answer)

if session.error:
    st.error(session.error)
    st.caption("Your input is preserved. Check your Gemini key, internet connection and API quota.")
    if st.button("↻ Retry this decision", type="primary"):
        run_turn()

if session.result:
    reply = session.result.reply
    if reply.kind == "recommendation":
        with st.container(border=True):
            if session.locked_id is None:
                st.caption("THE VERDICT")
                st.subheader(reply.recommendation)
                st.markdown("**Why this fits**")
                for reason in reply.reasons:
                    st.write("• " + reason)
                if reply.assumptions:
                    with st.expander("Assumptions behind this choice"):
                        for assumption in reply.assumptions:
                            st.write("• " + assumption)
                st.divider()
                st.caption("YOUR NEXT MOVE")
                st.write(reply.next_action)
                st.caption("Ready when you are. You make the final call.")
                if st.button("🔒 Lock This Decision", type="primary", use_container_width=True):
                    try:
                        session.lock(store)
                        st.rerun()
                    except StorageError:
                        st.error(
                            "I made the recommendation, but I couldn’t save the lock locally. "
                            "You can still copy the next action."
                        )
            else:
                st.success("🔒 Decision locked.")
                st.subheader(reply.recommendation)
                st.write("Overthinking privileges suspended until this task is done.")
                st.divider()
                st.caption("YOUR NEXT MOVE")
                st.write(reply.next_action)
                st.markdown("**Was this actually useful?**")
                for column, label, helpful in zip(
                    st.columns(2), ["👍 Yes", "👎 Not really"], [True, False]
                ):
                    if column.button(label, use_container_width=True):
                        try:
                            session.feedback(store, helpful)
                            st.rerun()
                        except StorageError:
                            st.error(
                                "Your lock is saved, but feedback couldn’t be saved. Try again."
                            )
                if session.feedback_value is not None:
                    st.caption("Thanks — saved. You can change your feedback anytime.")
            st.download_button(
                "Copy as a text file",
                data=f"{reply.recommendation}\n\n{reply.next_action}\n",
                file_name="next-move.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with st.expander("How this decision was made"):
            st.caption(
                f"{session.result.provider} · {session.result.elapsed_seconds:.1f}s "
                "for this response"
            )
            if not session.result.tools:
                st.write("The agent did not execute a decision tool on this turn.")
            for observation in session.result.tools:
                st.write(f"**{observation.name}** · {observation.result.get('status', 'executed')}")
                if observation.name == "score_options" and observation.result.get("status") == "ok":
                    rows = [
                        {"Option": row["name"], "Score / 10": row["weighted_score"]}
                        for row in observation.result["ranked_options"]
                    ]
                    st.dataframe(rows, hide_index=True, use_container_width=True)
                    st.caption("Weighted judgments, not probabilities. Higher is better.")
                    st.json(observation.result, expanded=False)
    elif reply.kind in {"information", "refusal"}:
        with st.chat_message("assistant"):
            st.write(reply.message)

finished = session.result is not None and session.result.reply.kind != "clarification"
if not finished:
    st.checkbox(
        "Use my locked decisions for this choice",
        key="allow_history",
        help="Allows the agent to read your local history. Retrieved history "
        "is sent to Google along with your request. Leave off for a fresh decision.",
    )
    if session.clarification and not session.answer:
        st.caption("One quick answer, then we’ll choose.")
    text = st.chat_input(
        "Answer the question…" if session.clarification else "What are you deciding?",
        max_chars=4000,
        disabled=bool(session.error),
    )
    if text:
        run_turn(text)
else:
    st.button("Make another decision", on_click=new_decision, use_container_width=True)

st.caption("The agent recommends. You decide. · Gemini API · Built with Strands")
