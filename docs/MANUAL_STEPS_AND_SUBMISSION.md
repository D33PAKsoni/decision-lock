# Final Gemini demo and submission checklist

## Local setup

Extract the setup ZIP where you want the app, then run Setup.cmd. It creates a Lock
folder beside the setup, installs dependencies, runs offline tests and prompts for a
masked Gemini key. There is no Ollama installation or model download. Use a free-tier
Developer API project if you want to avoid charges; the app cannot check billing/quota.

Use Lock/Start Lock.cmd on later launches. Use Set Gemini Key.cmd to replace a saved
key. Use Run Live Tests.cmd to verify genuine model responses and tool invocation.
The Windows encrypted key is user-specific; never share .gemini-key.dpapi or a private .env.

## Live verification

- [ ] Run Run Live Tests.cmd; ensure two tests pass rather than skip.
- [ ] Confirm the provider label says Gemini API and the actual model used.
- [ ] Open How this decision was made; verify a real score_options execution.
- [ ] Check one recommendation, 2–4 concise reasons and a concrete next move.
- [ ] Verify the lock saves, thumbs feedback persists and new decision recalls permitted history.

Offline protocol fixtures are not real model runs. Automated thumbs votes are test
assertions, not evidence that a person liked the result. Record only real observations.

## Ten scenarios to record

| # | Prompt / condition | Observe |
|---|---|---|
| 1 | Exam tomorrow vs undated side project, 30 minutes | Clear verdict and next action |
| 2 | Gym vs assignment due tomorrow, 45 minutes | Respects time/deadline |
| 3 | Event vs work due tonight | Missing key facts handled honestly |
| 4 | Low-cost notebook now vs wait; old one works | Practical choice without certainty claims |
| 5 | argparse vs a framework for a small Python CLI | Assumptions disclosed |
| 6 | Blocking bug vs colors, 30 minutes | Explicit priority and limit respected |
| 7 | Study or build, no deadlines given | At most one structured clarification |
| 8 | I don’t know what to do tonight | Useful single clarification or honest information |
| 9 | Temporarily disconnect internet or use a deliberately invalid key | Friendly failure, retained input, retry; restore key afterward |
| 10 | Lock/feedback, new choice, recall prior decision | History permission and persistence |

Also run the explicit numeric scoring prompt from README. Expected arithmetic is 8.3
and 6.1. Log scenario, provider/model, clarification count, tools actually executed,
verdict, next action, lock/feedback result and any problem. At least eight realistic
scenarios need actual execution before claiming completed scenario testing.

## Genuine screenshots

Save reviewed PNGs under assets/screenshots/:

- 01-first-run.png: title, explanation, examples and actual Gemini provider label.
- 02-agent-recommendation.png: real input, verdict, reasons and next move.
- 03-decision-locked.png: actual saved state and thumbs controls.
- Optional 04-tool-evidence.png: scoring tool and factor breakdown.
- Optional 20–40 second recording: request → verdict → lock → feedback.

Do not include keys, account/billing screens, private prompts or unrelated tabs.
No simulated screenshot is included in the code release.

## Public release and Builder article

Run python scripts/check_release.py. Exclude private .env, encrypted key, databases,
caches and virtual environments. Manually review screenshots and any Git history.
The scanner flags private runtime files after app usage; exclude those from publication
rather than deleting personal data just to make a scan green.

Read BUILDER_ARTICLE_DRAFT.md. After real API runs, replace its pending-evidence/testing
passages with your actual observations and embed the genuine proof. Do not publish the
build-review note above the article body. Describe Strands as the AWS-origin tool used
and Gemini as the model actually invoked. Do not claim Bedrock or AWS hosting.

- [ ] Real tool-using agent is demonstrated.
- [ ] Delightful lock detail and genuine observation of its usefulness are described.
- [ ] Article is 500+ words and includes what/who, how built, delight/testing and proof.
- [ ] Tag is #agents.
- [ ] Builder profile includes image, country and About.
- [ ] Article reviewed and published from your Builder account.
- [ ] Published tag/screenshots render correctly; URL saved.
- [ ] Public GitHub source reviewed and published if desired (optional).

The published rules do not mandate Ollama or Bedrock. Our reading is that Strands plus
Gemini fits the listed provider-independent requirements; organizers decide qualification.

Deadline verified October 12: October 12, 2026 at 20:00 UTC = October 13, 1:30 AM IST.
https://builder.aws.com/content/3JnXmg1PikRXrSSDFHWEOw5RAur

No API success, human feedback, deployment, publication or eligibility award is claimed
by the automated offline build. Finish the genuine demo before submitting.
