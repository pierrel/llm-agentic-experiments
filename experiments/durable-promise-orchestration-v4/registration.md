# Durable-promise orchestration v4

Status: unsealed development design. This version follows the incomplete v3
todo-rider screen and its pre-admission interruption record. V3’s 16 completed
episodes remain directional negative evidence only and are excluded from every
v4 calculation.

## Question and causal contrast

On top of the exact durable-memory C1 guidance confirmed by
`durable-promise-outcome-v2`, does a general web-main lifecycle instruction
improve durable capture and mixed-turn completion after asynchronous evidence
returns?

`C0` is the current durable-memory candidate with no new lifecycle text. `C1`
differs only by this paragraph, inserted once in the ordinary web-main
`Async task lifecycle` section immediately after the existing instruction to
retrieve and use a trusted terminal result:

> After checking a terminal task result, reconcile the independently valuable
> outcomes of the user's current request before replying. Use checked evidence
> for outcomes that depend on it, then complete every remaining requested outcome
> that can now be completed correctly. For a future conditional action, complete
> the durable outcome by preserving its condition and requested action in thread
> memory; do not perform or claim the future action now. Do not substitute a
> reply or temporary tracking for that action.

The paragraph is present in both the launch and completion request prompts. Its
instruction applies only after a checked terminal result. It neither names nor
requires todos, skills, filesystem paths, or an eval fixture. The treatment
changes no tools, middleware stack, state, graph, task lifecycle, or memory
guidance.

## Development rows and measurement

The three natural rows in `tasks.json` are already exposed. They are useful
only to reject or nominate a candidate and cannot support a release claim. Each
fresh thread/sandbox receives a deterministic local context fixture, normal
ordinary-web-main graph, local Qwen endpoint, fixed decoding, and a completion
wake. Network access is blocked.

The primary outcome is strict full-row pass: the grounding skill/task/result
lifecycle, an answer using the checked local facts, a post-result
`/agent/memory.md` write that semantically retains the future condition and
requested action (`4` and `four` are equivalent where relevant), and no false
claim that a future action has happened or state was saved when it was not.
Routing, persistence, answer/honesty, todo use, and todo reconciliation are
separate diagnostics. The exact C1 text must appear exactly once in every C1
provider request and zero times in every C0 request; that is the manipulation
check. This study measures durable outcome capture, not whether a later future
trigger is fulfilled.

## Schedule and decision

There are three independent repetitions per condition per row: 18 fresh
episodes. The sealed generator uses schedule seed `2026082405`, balances C0/C1
positions within every row, and uses fresh recorded generation-seed labels;
the local server does not expose a usable generation-seed setting, so episodes
are independent rather than paired.

Do not stop early. Once a provider request begins, every timeout, refusal,
malformed result, or failed primary outcome is recorded and never replayed.
Admission denial or demonstrated pre-provider corruption may retry its exact
scheduled ID. The coordinator, not an outer command, is the sole LLM-admission
owner; a stale pre-admission `launch-intent` is retryable, while a
`model-invoke-started` marker never replays.

This exploratory treatment can advance only if all of the following hold:

- C1 has at least 7/9 full passes;
- C1 has at least two more full passes than concurrent C0;
- C1 has no full-pass deficit on any individual row; and
- C1 has no aggregate routing or answer/honesty regression.

Success nominates this exact fixed text for a new, unseen confirmation task
bank and concurrent regression panel. It is not evidence to ship directly.

## Design reviews

- Scientific integrity: approved the causal direction only after the literal
  text distinguishes future durable capture from performing a future action;
  requires a fresh sealed v4 and exclusion of v3 counts.
- Statistical rigor: requires the full 18 episodes, a C1 full threshold and
  concurrent improvement/no-loss gates, with no significance claim from this
  exposed N=3 screen.
- Harness fit: requires prompt exposure on every provider request, fresh source
  and schedule identities, one nested worker admission only, and no todo-based
  advancement rule. The implementation and tests record those requirements.
