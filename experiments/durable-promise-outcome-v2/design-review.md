# Durable-promise outcome completion v2: design review

Reviewed before the cohort's first model admission. This record preserves both
the v1 pilot limitations and the changes that make v2 a distinct confirmation
study.

## Scientific integrity

**Finding: v1's executable R/F advancement rule did not match its P/F prose.**
Resolved by treating v1 as a pilot only. V2 has fresh tasks, no tuning after v1,
and puts its P/F, sign-test, and protection rules in the sealed registration
consumed by the coordinator.

**Finding: a pilot's observed rows cannot become confirmation rows.** Resolved:
v2 has four new prompts, fixtures, facts, and commitment terms. It reuses only
the fixed treatment text through a hash-pinned reference to avoid accidental
prose drift or a misleading manual copy.

**Finding: opaque C0/C1 labels do not blind an operator who can read the prompt
traces.** Resolved by not claiming blinding. The primary oracle is deterministic
and the schedule, condition hashes, and decision rule are fixed before labels
are observed.

## Statistical rigor

**Finding: v1's three blocks per task were only partially position-balanced and
its raw counts did not adjust for that remainder.** V2 uses six blocks per task,
so each condition appears first and second exactly three times. It reports the
paired discordant-block exact one-sided sign probability, not a fictional
provider-seed pairing.

**Finding: pilot counts alone were insufficient for a release decision.** V2
requires both P and F to improve by at least six of 24 per condition, paired
support at `p <= 0.05`, and explicit R/A non-regression gates overall and per
task. These rules do not claim a population-level generalization from four task
shapes; task-level counts and intervals remain descriptive.

## Agentic harness fit

**Finding: the earlier source closure omitted shared accounting modules and a
recovery could claim a model request solely because a result file existed.**
Resolved: the implementation digest now includes the whole local runner and
shared `harness/` modules; recovery requires the provider-boundary marker before
it can preserve a worker result.

**Finding: PID reuse could make a dead worker appear live.** Resolved: lifecycle
markers now carry a Linux start-time and command-line digest, which recovery
compares before treating a process as alive.

**Finding: declared decoding/reasoning and provider identity were weaker than
the actual model invocation.** Resolved: the worker passes the sealed
temperature and reasoning values to model selection, and checks model id,
context length, and a non-secret endpoint digest before the first request. The
server does not offer a trustworthy weights hash, so v2 deliberately records
that limitation rather than pretending to bind unavailable evidence.

## Minimum adequate setup

The ordinary web-main graph, deterministic context-completion wake, private
thread-memory path, and blocked network are necessary to test the mixed local
fact plus durable outcome shape. No time, schedule, memory tool, middleware,
or production code is changed. We rejected additional task categories,
qualitative judging, and new mechanisms because they would add confounds or
researcher discretion without answering the fixed prompt-text question.

The shared GPU wrapper remains an operational invariant: same-user code cannot
turn it into a security boundary. The supported runner command is mechanically
tested to nest every worker under the wrapper, and every admitted episode is
bounded and independently recorded.
