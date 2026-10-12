# Deploy Decision Lock as a public Streamlit demo

The localhost Deploy error means the running app has no published GitHub remote.
The repository must exist on GitHub with its current branch pushed before Streamlit
can deploy it. Deployment uses this prepared source; no Windows setup is run on Cloud.

## 1. Put the prepared project on GitHub

Create a repository named decision-lock (a public source repository is suitable for
portfolio/demo use). Extract the Cloud ZIP and upload the CONTENTS of its project
folder at the repository root. Do not upload the ZIP as one file.

The root must contain streamlit_app.py, app.py, requirements.txt, decision_lock/,
.streamlit/config.toml and .streamlit/secrets.example.toml. The latter is a template
with placeholders, not a real credential. Include the supplied tests/docs/license.

If using Git locally in that clean project folder:

```powershell
git init -b main
git add .
git commit -m "Prepare Decision Lock public Gemini demo"
```

Add the actual repository URL shown by GitHub, then push main. Authenticate through
your Git client; do not paste GitHub credentials into this article or chat. If Git
is not installed, GitHub's Add file > Upload files also works for this small project.
Do not initialize a second repository inside the old Lock folder with private runtime files.

## 2. Create the Community Cloud app

Sign in at https://share.streamlit.io/ and connect the GitHub account/repository.
Click Create app > Yup, I have an app. Select:

- Repository: your decision-lock repository.
- Branch: main.
- Main file path: **streamlit_app.py** (not the local-only app.py).
- App URL: your preferred available subdomain.
- Advanced settings > Python version: **3.12**.

Paste these ROOT-LEVEL TOML settings in Advanced settings > Secrets, replacing the
placeholder PRIVATELY IN THAT DASHBOARD:

```toml
GEMINI_API_KEY = "YOUR_API_KEY"
GEMINI_MODEL = "gemini-3.5-flash-lite"
MODEL_PROVIDER = "gemini"
APP_MODE = "public_demo"
APP_TIMEZONE = "Asia/Kolkata"
DEMO_MAX_REQUESTS = "50"
REQUEST_TIMEOUT_SECONDS = "180"
MAX_MODEL_CALLS = "8"
```

Do not paste dotenv syntax into that field: TOML strings need quotes. Do not put the
real secret in GitHub. The Windows .gemini-key.dpapi file cannot be used by Linux Cloud.
The hosted app needs the real key through Streamlit's Secrets service.

Save settings, then Deploy. Wait for the app to finish starting; inspect Cloud logs
if dependencies or credentials fail. In Sharing settings, choose the public/searchable
option for the requested public demo. A public repository normally makes the app public
by default; verify the actual deployed Sharing setting rather than assuming it.

## 3. Verify the actual public URL

Test the published page in two separate browser sessions. Each must have its own empty
history; lock a choice in one and verify it is not visible in the other. Run a real
scoring prompt and inspect the evidence expander, then verify lock/feedback and next-action
download. Capture genuine hosted screenshots for the challenge article.

The Cloud entry forces public-demo behavior even if APP_MODE is accidentally left local.
Public visitors cannot change the owner's Gemini model through the UI.

## Limits of this demonstration

- Histories use separate temporary SQLite files for each browser session. New decision
  reuses that session's history; another session does not. Refresh/disconnect/restart
  can reset data. There is no durable hosted database or account-based history yet.
- Community Cloud does not guarantee persistence of local files. Download a next action
  if you want to keep it. Your Windows database is not uploaded or migrated.
- The shared Gemini key uses the owner's API quota. Use a free-tier project for the
  intended zero-cloud-inference-charge path; the app cannot check billing status.
- Default budget is 50 agent requests per server process across all visitors. Failed
  requests count. Multiple model/tool turns can occur inside one request. This is a
  simple process budget, not a financial cap, a distributed rate limiter or protection
  against every kind of abuse. Rebooting resets it; adjust via DEMO_MAX_REQUESTS deliberately.
- Code deployment is not proof that Gemini works. Test the actual key/model on the final URL.

## Source checks

94 offline tests passed with 2 live tests skipped during preparation. Ruff and source
secret/artifact checks passed. No real key, .env, encrypted key, personal database,
virtual environment, cache or fabricated screenshot belongs in the deployment package.
Repository publication, hosted launch, actual API calls and user feedback must be
reported only after they are verified. Preparing this package does not claim deployment.

Official references checked October 12, 2026:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app
https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
