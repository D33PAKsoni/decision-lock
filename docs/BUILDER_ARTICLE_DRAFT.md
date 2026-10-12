> Build-review note — not part of the article: this 500+ word draft reflects current
> automated verification. Before submission, complete a genuine live-model demo,
> replace the pending-proof/testing passages with actual observations and embed screenshots.
> Do not publish this as a completed challenge entry yet.

# I Built Decision Lock to Turn Small Choices into One Next Move

## What it does and who it is for

Decision Lock is a small AI agent for the everyday choices that take longer than they
deserve. It is intended for students and personal builders choosing what to work on,
how to use a short block of time, or which practical option fits their priorities.

One example is: “Should I study for my AWS exam tonight or work on my side project?”
A useful answer needs to account for the exam date, available time and what matters to
the person asking. It should also leave them with something they can actually do next.

I wanted the experience to end in a clear action. Decision Lock accepts a natural-language
choice, asks up to four relevant context questions, offers an editable context review, and presents one recommendation, a few short
reasons and one next move. The user then has an explicit Lock This Decision button.
The agent recommends; the person makes the commitment.

The scope is deliberately small: study, projects and ordinary plans. The agent's
instructions redirect medical, legal, emergency and high-stakes financial requests
instead of trying to make those decisions.

## How it is built

The implementation uses Python 3.12, Streamlit, the Strands Agents SDK and local SQLite.
Streamlit provides the interface, while Strands runs the model-and-tool loop. The model
can choose tools, consume their results and synthesize the verdict. The application
does not impose a fixed sequence of tool calls for every prompt.

The central tool is `score_options`. It compares two to five options against weighted
criteria, validates scores from zero to ten, normalizes weights and returns a factor
breakdown. Higher scores always mean a better fit. Missing values produce a structured
request for clarification instead of being silently filled in.

This separation matters because a language model can explain tradeoffs while ordinary
Python handles arithmetic. Urgency, importance, effort-fit and reversibility scores
of 9, 8, 8 and 7 with weights of 0.4, 0.3, 0.2 and 0.1 produce 8.3. The tool reports
ties explicitly and treats numbers as judgments rather than probabilities or guarantees.

Two other tools provide local time and recent locked decisions. History is private
by default. An explicit checkbox enables access, and the tool checks that permission
before reading SQLite. It does not rely only on the model following an instruction.
This makes the data boundary understandable when using a remote model.

The model provider is the Gemini Developer API, using the Strands Python Gemini adapter.
The default is gemini-3.5-flash-lite, a stable model that Google lists with function
calling and structured output support. A private API key is required, and the application
has no local model download. I chose this path to reduce installation overhead on the
computer running the demonstration. Google lists a free tier for this model, although
actual access and quotas depend on the API project.

Strands is the AWS-origin agent tool used in this build. No AWS infrastructure was deployed
and no Bedrock inference is claimed. The app and SQLite storage run on the user's computer,
while prompts and permitted tool results go to Google's API. The real Gemini demonstration
is still pending at the time of this draft because no API credential was supplied to the
build workspace.

The Windows installer also follows the user's chosen directory: it creates Lock beside
the setup script. It prompts for a key without displaying it and retains a copy protected
by the Windows user's encryption. That private file is excluded from public releases.

## The delightful detail: an actual ending

The detail I wanted to test is the transition from recommendation to commitment.
Before locking, the card shows the verdict, reasons and next action. After the person
clicks Lock This Decision, it changes to a saved locked state, repeats the next move
and adds a small line of personality: “Overthinking privileges suspended until this
task is done.” Thumbs-up and thumbs-down controls ask whether it was actually useful.

Locking is a human action rather than an agent tool. SQLite records the choice only
after the click. A unique token prevents repeated clicks or save retries from creating
duplicates. Feedback belongs to that record and can be changed without inflating vote
counts. Previously locked choices are available in the sidebar.

Friendly recovery is part of the same experience. If the model is unavailable, the app
retains the input and offers a retry. If saving fails, the recommendation remains
visible and the next action can still be downloaded as text. The person should not
lose progress just because one part of the system fails.

## What has been verified so far

The automated suite has 108 passing tests and two live-Gemini tests that skip unless
explicitly enabled. Tests cover weighted arithmetic, validation, persistence, feedback,
key/provider configuration, privacy checks, timeouts and the bounded context-and-review contract.

A scripted protocol fixture exercises the actual installed Strands loop: it requests
a tool, the real Python tool executes, and the result returns to the fixture before
the structured verdict is produced. This checks SDK wiring. It does not establish
that a real model reasons well or chooses tools correctly; that distinction matters.

Streamlit's application test harness verifies recommendation, lock, feedback, retry and
clarification interactions, including storage failures and model-setting validation.
Those tests verify behavior, not whether people enjoy the result. No human helpfulness
findings or response-latency measurements have been collected for this draft.

## Proof and the next validation step

A genuine live-model run is the remaining verification step. The source includes
opted-in smoke tests for a real recommendation and scoring-tool invocation, plus ten
manual scenarios covering time pressure, missing context, errors and history recall.
The final article needs real screenshots of the recommendation and locked state,
with observations from those runs, before it can serve as working-agent proof.

The lesson from the implementation is practical: a narrow agent can have clear boundaries
around tools, personal data and human commitment. Decision Lock is built around that
small workflow, with one visible next action as its destination. The remaining demo
will show how well the selected Gemini model delivers it in practice.

#agents
