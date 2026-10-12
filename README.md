# Decision Lock 🔒 — public Gemini demo

A Strands agent for small practical choices: one recommendation, one next move,
then an explicit human lock. Python 3.12, Streamlit, Gemini Developer API and SQLite.

## Deploy on Streamlit Community Cloud

Upload the contents of this folder to a GitHub repository, commit/push main, then use:

| Setting | Value |
|---|---|
| Branch | main |
| Main file path | streamlit_app.py |
| Python | 3.12 |
| Dependency file | requirements.txt |

Put the Gemini key privately in Community Cloud Advanced settings > Secrets.
Copy .streamlit/secrets.example.toml and replace YOUR_API_KEY only in that dashboard.
Never upload a real secrets.toml, .env, encrypted key or personal SQLite database.

See [the complete deployment guide](docs/STREAMLIT_DEPLOYMENT.md) for exact steps.
The Cloud entry isolates each browser's temporary history, hides model changes from
visitors and limits agent requests to 50 per server process by default. The request
budget resets on restart and is not a financial spending cap. Public usage consumes
the owner's Gemini quota. Use a free-tier project if you want to avoid API charges.

## Local development

Use Python 3.12. Install with python -m pip install -e '.[dev]'. Privately configure
GEMINI_API_KEY, then run python -m streamlit run streamlit_app.py to test public-demo
behavior. Run python -m streamlit run app.py for local persistent single-user history.

## Context-first flow (v0.3)

Describe your choice. The agent asks 2–4 relevant questions when context is sparse,
skipping facts you already supplied. It can ask a follow-up within a strict maximum
of four questions total. Answers are optional: **That’s enough — review now** moves
straight to review and preserves partial answers. Missing facts remain unknown.

Review and edit **Here’s what I understood**, then click **Confirm context & compare**.
Only then can the agent recommend. **Lock This Decision** remains a separate human
confirmation. The saved decision and downloaded next-action file include your reviewed
context. Fully specified requests can move directly to review; history recall and
out-of-scope requests can return an explanation without a lockable recommendation.

Context and recommendation requests consume the same demo quota. A complete flow usually
uses three API requests (questions, summary, comparison), or four with a follow-up.
Public-demo history remains temporary and separate for each visitor.

## Verification

108 offline tests passed; 2 opted-in live API tests skipped. Test coverage includes
real Strands protocol execution through fixtures, actual Gemini adapter request formatting,
scoring/storage/feedback, input-preserving retry, Cloud session isolation, forced public
mode and atomic process-wide request reservations. Scripted fixtures are not real model
inference. No public deployment success is claimed by source preparation.

Ruff and the source secret/artifact scan pass. Live hosted/API testing requires the
owner's credentials and a verified deployed URL. History in Community Cloud is temporary;
local file storage is not guaranteed to survive restarts/disconnects. Download next actions
to keep them. Permanent multi-user account history is outside this demonstration.

MIT licensed. Strands is the AWS-origin tool used; no AWS infrastructure is required.

## v0.3.1 — final response recovery

If the Strands loop reaches its budget or fails to finish structured output, one reserved
call uses Gemini's native JSON-schema response to complete the current phase. It receives
the original request, reviewed context and only actual recorded tool results. It does not
invent a local verdict or execute extra tools. Overall timeout and model-call caps remain
bounded. Per-call output headroom is 4,096 tokens; the tool loop output cap is 8,192 tokens.
A sanitized stop reason is logged without prompts, answers or API keys. Quota, authorization
and safety failures are not converted into fabricated decisions. Live API testing is still
required after deployment; automated recovery tests use SDK protocol fixtures.
