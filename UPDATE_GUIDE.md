# Upload v0.3.1 to your existing GitHub repository

1. Extract this ZIP. Its root contains app.py, streamlit_app.py and requirements.txt.
2. In D33PAKsoni/decision-lock, choose Add file > Upload files.
3. Upload the extracted contents at the repository root, replacing existing versions.
   Do not upload the ZIP itself or add an extra enclosing project folder.
   Include the complete decision_lock folder: its models, controller, agent and prompt
   files must be updated together with app.py. Include tests and docs as well.
4. Commit to main with message: Recover incomplete Gemini verdicts with bounded native output.
5. Streamlit will normally redeploy after the commit. If it still shows the old flow,
   use Manage app > Reboot app, then refresh the app.
6. Keep your existing Streamlit Secrets, Python 3.12, main branch and streamlit_app.py entry.

Smoke check: submit Study or build? Answer the topic-specific questions, review and correct
Here’s what I understood, select Confirm context & compare, then lock the recommendation.
Also try That’s enough — review now with blank/partial answers. No lock button should appear
before a recommendation. Test a new browser session to confirm history stays separate.

No database migration, local model download or new dependency is required. Public-demo
history remains temporary. Context gathering adds Gemini requests, which count toward the
existing per-process demo limit. This archive contains placeholder configuration only.

For this hotfix, agent.py and providers.py under decision_lock are essential. Upload the
whole extracted archive to keep code, tests and docs consistent. Existing Streamlit Secrets
can stay unchanged, including MAX_MODEL_CALLS=8 and REQUEST_TIMEOUT_SECONDS=180. After the
commit, reboot the Streamlit app if needed and start a fresh decision. Do not keep repeatedly
retrying the older deployment: each request consumes your Gemini/demo quota.
