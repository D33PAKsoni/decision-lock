# Gemini release verification — October 12, 2026

Runtime: Python 3.12.14. Strands 1.59.0, Streamlit 1.65.0, Google GenAI 2.29.0.
This release replaces the original Ollama/Bedrock adapters with Gemini Developer API.

## Actual automated results

- `python -m pytest -q`: **89 passed, 2 skipped**. The skipped tests are opt-in live
  Gemini generation and scoring-tool tests. No API credential was supplied for this build.
- `ruff check .`: passed.
- `python -m pip check`: no broken requirements.
- Source secret/artifact scan: 45 text files checked, zero flagged items.
- Both ZIPs passed archive integrity checks and private-file exclusion checks.

## Scope

The retained core tests cover deterministic scoring, missing/invalid inputs and ties,
SQLite persistence and idempotent locking, correctly associated/updatable feedback,
current time, history privacy, one-clarification state, input-preserving retry and bounds.

Gemini-specific tests cover secret-free Settings, absent API key, key alias/precedence,
current SDK construction, Developer API selection (Vertex disabled), HTTP limits and
actual adapter formatting of the application's tool declarations. API-error tests verify
quota/access/model errors are friendly and do not expose exception payloads in UI or logs.
Doctor is tested to initialize without network generation and without displaying the key.

The actual Strands loop is exercised with scripted tool-use protocol fixtures and real
Python tools. These tests do not validate a learned model's judgment or tool selection.
Streamlit AppTest covers first run, clarification, verdict, lock/feedback, new choice,
retry, storage failure and model setting validation/reset. It does not verify browser layout.

## Setup and verification limits

The installer targets Lock alongside Setup.cmd, not Desktop. It installs no Ollama/model.
The Windows startup code uses a masked key prompt and Windows user DPAPI encryption,
then passes a decrypted key through the child environment. Live tests are explicitly invoked
by Run Live Tests.cmd. Source/archives contain no real key or generated encrypted key.

Python launcher syntax and archive structure are checked. Windows installer execution,
DPAPI round-trip and browser launch cannot be executed in the Linux build environment.
Actual Gemini authentication, response latency, reasoning/tool selection and free-tier
account availability remain unverified until the user's real-key tests run.

No cloud infrastructure, billing upgrade, real API inference, user-feedback study,
GitHub publication or Builder Center publication was performed. There are no fabricated
screenshots, provider success claims or scenario completion counts.

## Next steps

Run Setup.cmd in your chosen folder, privately configure a Gemini key, then Run Live
Tests.cmd. Ensure two tests pass rather than skip. Complete the real scenario/screenshot
checklist, update the article with genuine proof/observations, and review/publish it.

## Community Cloud preparation update — October 12

94 tests passed, 2 live API tests skipped. Added coverage proves per-session storage
isolation/stability, retained local history path, atomic process-wide request reservations,
two separate AppTest browser histories, hidden public model settings and forced public
mode through streamlit_app.py. Ruff checks pass. No live deployment/API success is implied.
