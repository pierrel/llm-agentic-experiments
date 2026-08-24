# Durable-promise orchestration v1: development result

Status: reported development experiment. No Assist candidate was shipped.

## Scope and outcome

This report records the prompt-only development experiment registered at
`experiments/durable-promise-orchestration-v1/registration.md`. Each episode
used a fresh local web-main thread, the local Qwen model, deterministic context
task evidence, and no live search. The frozen primary oracle required all of:

1. the grounding lifecycle,
2. the grounded local answer,
3. a private `/agent` commitment containing the later condition and response,
4. an honest final reply.

The unit is one fresh model episode. Raw traces remain local; this report keeps
only aggregate results and the observed failure class.

## Method limit

This was an Assist-side exploratory run using its existing eval helper and a
temporary driver, not a sealed laboratory-harness run. It did not capture the
rendered provider prompt, complete settings bundle, randomization schedule, or
raw-trace hashes required for a reproducible lab result capsule. The scores are
therefore directional product evidence only, not a scientific confirmation or
a basis for a statistical claim. The registration remains useful as a record of
the intended question and frozen rows; a future lab study must re-register and
run through the sealed harness.

## Control

The unmodified current prompt scored 0/3 on each development row (leading,
trailing, and explicit future-check-in) and 0/3 on each holdout (workshop and
budget) under the complete frozen oracle. It usually answered the local question
but did not persist the later request. On the workshop and budget rows it also
sometimes loaded time, scheduling, or event skills before grounding. Those are
control observations, not candidate regressions.

## Candidate exploration

| # | Declared treatment | Development evidence | Interpretation |
|---:|---|---|---|
| 1 | Minimal todo rider | Leading 0/3; no todo calls | Rider was exposed but ignored. |
| 2 | Explicit two-outcome todo rider | Leading 0/3; no todo calls | Tightening the todo threshold did not change behavior. |
| 3 | General outcome-completeness reminder | Leading 0/3 | Sometimes created a todo, but tracked transient profile facts in user-visible memory instead of the commitment. |
| 4 | Thread-memory later-commitment rule | Leading 2/3; trailing 0/3 | Correct placement was possible, but order in the user message dominated. |
| 5 | Mixed-request commitment classification | Leading 1/3; trailing 2/3; future 3/3 | Clear semantic signal, but future rows often wrote between task launch and result retrieval. |
| 6 | Same rule with an after-grounding sentence | Future check started 1/1 | The model still wrote before result retrieval; the treatment was not advanced. |
| 7 | Repository-memory scope exclusion plus thread rule | Future 0/3 | Caused the private write before `load_skill("grounding")`; rejected. |
| 8 | Source candidate: grounding ordering plus thread rule | Future 3/3; leading 0/3 | Helped explicit future wording but failed quoted future conditions. |
| 9 | Source candidate plus quoted-future distinction | Leading 3/3; trailing 1/3 | Correctly distinguished “when I tell you,” but trailing wording still produced unsupported saved claims. |
| 10 | Final source candidate plus write-before-claim rule | Leading 3/3; trailing 3/3; future 2/3 | Best development result: 8/9 versus control 0/9. One future run used an invalid relative `agent/memory.md` path; several rows still wrote before the context result. |

Treatments 8–10 changed only Assist prompt/skill prose. No runtime or
middleware behavior changed. Treatment 10 was reverted after confirmation
holdouts failed.

## Confirmation holdouts for treatment 10

| Frozen row | Control | Candidate | Result |
|---|---:|---:|---|
| Makerspace orientation plus shelf commitment | 0/3 | 0/4 | No improvement. The agent often loaded time before the context task, then claimed the shelf commitment was saved without writing it. One run did write it but still violated the grounding-first oracle. |
| Internet-bill due date plus budget commitment | 0/3 | 0/4 | No improvement. The agent often loaded scheduling, time, and event capabilities and skipped grounding entirely; one run persisted only the commitment while claiming the due date was unknown. |

The N=5 confidence runs stopped after four consecutive starting failures under
the workspace evaluation rule. The candidate therefore did not meet the
shipping criterion of broad improvement without important regressions, even
though its development score was materially better.

## Learning and next experiment

The evidence supports a narrower claim: wording that distinguishes a quoted
future condition from a current report, names the private storage scope, and
requires a successful write before claiming success can improve an uncomplicated
grounded mixed request. It does not survive competing skill-routing decisions.

The next registered study should isolate the interaction between grounding and
competing date/schedule/event skills. It should test a general grounding-first
invariant without reusing these user prompts or adding task-specific wording.
That is a new causal question and requires a new registration and frozen task
split before any model runs.
