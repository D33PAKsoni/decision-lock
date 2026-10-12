# v0.3.1 verification — context before commitment

Python 3.12.14: 108 offline tests passed; 2 opt-in live Gemini tests skipped.
Ruff checks and formatting pass. Release scan excludes secrets and runtime data.

Coverage includes real Strands protocol fixtures executing Python tools; phase-specific
structured output; bounded adaptive questions; partial/skipped answers; editable context
passed to final comparison; rejection of premature recommendations and locks; retries
without duplicate answers; preserved corrected context after a failed comparison; lock
idempotency and feedback; Streamlit question/review/lock controls; session isolation,
forced public mode, provider error handling, and request budgets.

Fixtures do not establish real Gemini question quality or end-user enjoyment. No API key
was supplied to this build workspace, so the new hosted flow needs the owner's live check.
Existing production operation reported by the owner predates this context-first update.

Recovery regression tests reproduce loop-budget exhaustion, invalid structured-tool output,
SDK structured-output and token-cutoff exceptions, review-stage recovery and native-finalizer
timeouts. The real Gemini adapter is exercised against an offline response fixture to verify
native JSON MIME type, response schema, output token headroom and validated parsing.
