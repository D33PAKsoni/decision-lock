# Cost and credential guardrails — Gemini release

- The updated project uses Gemini Developer API; it does not install Ollama or call Bedrock.
- It retains AWS-origin Strands orchestration without deploying any AWS resources.
- Google's current pricing lists a free tier for the default model. Access and quotas
  depend on the API project. The app cannot verify the billing tier or guarantee no charges.
- Use a free-tier project for a zero-cloud-inference-charge path. Do not enable paid
  billing solely for this demo. On paid projects, generation/live tests may be metered.
- No Google grounding, web search, cloud storage or other paid add-ons are enabled.
- Vertex AI is explicitly disabled in the adapter.
- Standard tests and doctor are offline. Live tests require RUN_LIVE_TESTS=true.
- Turn/token/time bounds prevent endless loops but are not financial caps.
- Keys live in the private process environment; Windows startup supports a user-encrypted
  .gemini-key.dpapi file. Never share it, a private .env, database or credential screenshot.
- Prompt and permitted history/tool results go to Google; review API free-tier data-use terms.

No real API inference, cloud resources, billing upgrade or publication was attempted here.
Source: https://ai.google.dev/gemini-api/docs/pricing
