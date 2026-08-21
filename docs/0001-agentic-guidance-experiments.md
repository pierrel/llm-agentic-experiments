# Design 0001: controlled agentic-guidance experiments

## Purpose

Measure how model-facing guidance changes an agent's observable behavior. The
research question is not whether a sentence sounds clearer to us. It is whether
the same small model chooses the intended affordance, produces the requested
artifact, and avoids unwanted work under a controlled agentic loop.

This laboratory is separate from Assist so exploratory prompts, fixtures, and
negative findings cannot quietly become product behavior.

## In plain English

An *agentic* experiment lets a model take several turns and use tools instead
of asking it for one answer. A user asks for an outcome. The model can read or
write a fresh fake workspace, load an instruction document called a skill, or
ask a fake specialist. A fixed automatic checker then decides whether the
requested file or state exists and is correct. We save a chronological record,
called a trace, of the prompts, model messages, tool calls, and tool results.

The point is to compare versions of the same setup. A *condition* is one
version; a treatment contains the intentional guidance change and a control is
the comparison version. We preregister: commit the question, procedure,
scoring rule, and analysis plan before seeing model results. That prevents us
from quietly changing the test until our preferred prompt wins.

## Shared experimental model

Every study uses a minimal agent with:

- a system prompt and one natural user request;
- a stateful virtual workspace with deterministic files;
- tools for read, write, list, execute-like deterministic transforms, and a
  `load_skill(name)` progressive-disclosure tool;
- optional specialist-task tools with canned, typed results;
- a bounded tool loop, complete trace, and deterministic final artifact oracle
  (an automatic checker with a fixed pass/fail rule for a file or state change).

The harness owns the loop and fixtures. A study supplies only its treatment
manifest, task matrix, and oracle. It must capture the exact provider request,
tool schemas, tool results, model/version/configuration, fixture digest, random
seed, condition, and final trace for every trial.

No external network, repository, clock, user data, or live Assist state belongs
in a first-study fixture. The runner uses an in-memory or virtual workspace,
stable sorted filesystem responses, allowlisted pure transforms, and no shell
or host-filesystem access. Each request has a unique ID and the runner asserts
stateless API use. Synthetic tool data uses arbitrary names and values so model
memory cannot answer from a familiar fact.

## Study A: repetition, locality, and steerability

### Question

Does concise operational guidance repeated at the decision point improve an
agent's ability to choose and complete a required tool-mediated workflow?

### Hypothesis

For tasks where progressive guidance can help select a particular tool path, a
consistent local restatement in a loaded skill will improve total agent-policy
success and correct-path selection compared with the same rule expressed only
in the system prompt. This is not a forced-load locality estimate: whether the
agent chooses to load the skill is part of the observed policy. A later
forced-load study can isolate the narrower message-placement question.

### Conditions

This is a token-matched 2×2 study. The two factors are whether the exact
operational rule appears in the system prompt and whether it appears in the
loaded skill at the action step. Each absent-rule slot receives equal-length,
task-relevant, **non-operational** text. All conditions have the same tools,
skill catalog description, user request, fixture, decoding settings, and
token count for each corresponding fixed prompt slot within a preregistered 1%
tolerance using one pinned tokenizer/version. The runner still captures the
full per-turn provider-request token vector: later turns may legitimately
differ after a model selects a different tool path.

1. **Neither:** neutral system slot and neutral skill slot.
2. **System-only:** operational system rule and neutral skill slot.
3. **Local-only:** neutral system slot and operational local skill rule.
4. **Repeated:** the same operational rule in both slots.

The primary contrast is repeated versus system-only: the incremental effect of
making the repeated rule available through the relevant progressive skill after
the system rule is already present.
The factorial main effects and interaction are secondary, explanatory results.
This design distinguishes a local rule from raw extra text and makes clear that
it studies these two specific placements, not every possible form of
repetition.

The primary outcome is a deterministic success artifact. Secondary outcomes
are correct first consequential tool call, unwanted-tool count, tool-call
latency, and truthful final response. The treatment is not allowed to name a
fixture file, test, oracle, or expected tool argument.

For example, an illustrative task might ask the agent to update a short note.
It must read the note before editing it. Success means the final note has the
requested change and the trace records a read before the write. This example
explains the measurement; it is not a task or wording used by the experiment.

The initial task matrix has four workflow shapes: local inspection before edit,
report-backed specialist handoff, deterministic calculation after a fact
lookup, and bounded multi-entity delegation. Each shape has several independent
preregistered task instances. A result that appears in only one instance or
shape is a task-specific observation, not a general prompting conclusion.

## Study B: chosen progressive guidance versus automatic delivery

### Question

When the same guidance is needed, is total system performance better when an
agent requests it through `load_skill`, or when the host provides it
automatically before the first model decision?

### Conditions

1. **Chosen:** the catalog exposes the guidance. The agent may call
   `load_skill`; its returned body becomes the next model context.
2. **Automatic:** the same catalog and tools remain available, but a
   fixture-owned deterministic task label causes the host to append the exact
   guidance body as a declared system-context message immediately before the
   first model decision.
3. **Automatic neutral control:** the host appends an equal-token,
   non-operational body at the same point.

The automatic route comes from the fixture's declared task label, never a model
classifier. The label is invisible to the user, model, oracle, and qualitative
reviewer. If an automatic-condition agent calls `load_skill`, the normal tool
still succeeds and the duplicate load is recorded; disabling it would create a
different capability set.

In plain English, Study B asks whether the same words work better when the
model actively retrieves them or when the host supplies them. Its primary
comparison is intentionally a whole-policy comparison: host delivery happens
before the first decision, while chosen delivery happens after the model asks
for the skill. It does not claim that only the body source changed. A later
mechanistic study can force a load and compare its tool-result message with a
matched host message if we need that narrower answer.

The shared primary outcome is final artifact success. It estimates total system
performance, including the host's delivery choice and, in the chosen condition,
the model's decision to seek guidance. Skill-use rate, unnecessary loads, model
turns, prompt size, and latency are condition-specific process outcomes, not
common primary outcomes. A separate forced-load capability study may later
compare an identical loaded-skill body with an identical host-delivered body;
that isolates message-channel efficacy but does not answer the total-system
question.

## Scientific controls and statistical plan

Each study gets a preregistration manifest before its first model run. It fixes:

- hypotheses, conditions, primary and secondary outcomes, task matrix, model
  snapshot, decoding parameters, timeouts, exclusions, and analysis code hash;
- experimental unit: one fresh agent episode identified by confirmation task,
  replicate block, condition, and generation seed (when the provider honors
  seeds). A block balances run order; it does not make stochastic outcomes
  magically paired observations;
- randomization: a blocked schedule that interleaves every condition for each
  task/replicate block and rotates condition position evenly across whole cycles.
  Confirmation uses a whole number of such cycles or explicitly adjusts for the
  remaining position imbalance. The runner reuses a preregistered distinct
  generation seed across conditions only after a recorded seed-support
  calibration; if unsupported, it records that fact and treats block as a fixed
  adjustment for run-order/time differences rather than pretending outcomes are
  paired;
- sample plan: pilot N=10 per task-condition only checks feasibility, oracle
  reliability, and protocol cost. It never supplies an effect estimate for the
  confirmatory target. Before the pilot, the registration fixes a minimum
  worthwhile absolute success-rate improvement, 90% power, alpha/interval level,
  and a conservative simulation over baseline-rate assumptions. That simulation
  chooses a fixed confirmation N before confirmation labels exist;
- inference: effect sizes and confidence intervals first. With the small fixed
  initial shape matrix, the confirmation model uses fixed task-instance effects
  and reports each task result, rather than pretending four shapes estimate a
  population random effect. A later larger matrix can preregister a hierarchical
  task model that estimates both task-level and overall differences. Exact
  primary contrasts are named in advance; a named secondary family uses the
  Holm correction, a predeclared adjustment against chance findings from many
  checks;
- missingness and retries: every scheduled episode stays in the primary
  denominator, even when it times out or refuses. Timeout, refusal, loop-budget
  exhaustion, invalid tool call, and provider error score primary-artifact
  failure with a reason code. A harness fault is retained and may be rerun once
  only if a mechanical record proves that no model request was made; otherwise
  it is never replaced;
- stopping: no condition-level result inspection or label reveal until all
  confirmation records are deterministically scored. GPU pauses preserve the
  schedule and cannot select or discard trials. An admission denial is an
  administrative attempt, not a model outcome: retry the same sealed episode
  later and log the denial separately. Latency excludes admission queue time and
  is descriptive unless timing control is separately registered.

The runner writes one append-only local JSON record per trial and a manifest that lists
every scheduled trial, including failures and timeouts. It stores condition IDs
instead of treatment names in the trace; the analysis join unlocks labels only
after deterministic scoring. Prompt snapshots are captured before runs and
diffed mechanically to prove the treatment factor. Every model turn captures
the exact serialized request, message roles, tool schema/results, tool-choice
options, and token vector. An allowlisted diff describes the single declared
treatment difference. The manifest also records the tokenizer, model
binary/version, weights digest, provider payload, cache policy, and
harness/fixture commits.

Before its first model run, a study creates a content-addressed, tagged bundle
of its registration, conditions, task bank, blocked schedule, fixtures, tool
schemas, runner/dependency revisions, and analysis plan. The runner fails
closed when a hash differs. Results use an append-only manifest hash chain.
An amendment receives a new study ID; it never overwrites the original plan.
In plain English, this is a sealed snapshot whose fingerprint changes if its
contents change; each result records the prior fingerprint. A finalized local
seal detects accidental edits or removals when verified against its schedule;
the required immutable git commit/tag is the durable historical anchor.

## Contamination and bias guards

- Fresh process, fresh conversation, fresh fixture directory, and fresh tool
  state per trial.
- Canned tool results contain no condition name, instruction-shaped text, or
  source path outside the fixture.
- Shared prompt fragments are content-addressed. The runner refuses a condition
  if undeclared prompt, tool-schema, fixture, or decoding differences appear.
  The starter validator compares declared top-level rendered-request fields; a
  real study must preregister the narrower path-level allowlist it needs.
- User prompts are natural outcome requests. Architecture, tool, skill,
  routing, and assertion language is prohibited unless the study explicitly
  labels a row as capability coverage.
- Deterministic oracles execute before a blinded qualitative reviewer sees a
  trace. Reviewer packets replace condition names with opaque IDs.
- Development and confirmation task sets are disjoint. Each confirmation task is
  randomized across every condition in the same cohort. Prompt changes after
  development require a new preregistration and a new confirmation cohort.
- Opaque condition IDs do not guarantee human blinding: traces may reveal the
  delivery path. Deterministic artifacts remain primary. Optional qualitative
  review redacts treatment-specific messages where possible, uses two raters and
  a committed rubric, records agreement, and reports likely unblinding.
- The harness has self-tests that introduce an undeclared prompt, schema, or
  fixture difference; a missing scheduled trial; a leaked condition label; and
  a changed result record. The validator must reject all of them.

## What an eventual report will show

The static report is designed for inspection, not a leaderboard. It shows
success and uncertainty for every task and condition, the preregistered
contrast, first-tool matrix, prompt-token trajectory, timeout/error counts, and
an allowlisted prompt/schema/fixture diff. A plain-language first paragraph
states, for example, “local repeat succeeded X/Y times and system-only A/B;
the estimated difference was D percentage points.” It then says precisely what
that supports, and what it does not establish beyond this model, task bank,
agent loop, and decoding configuration.

## Shared-GPU coordination

All real-model commands must be invoked from the agentic workspace through:

```sh
/home/pierre/src/agentic/tools/agentic resource run llm -- <one bounded trial>
```

The harness exposes no `--direct-model` option. Its runner submits one bounded
trial at a time, records admission denials and resume attempts, and follows the
workspace production-priority protocol. If production is busy, it performs no
model work and continues analysis, fixture validation, or report generation.
No experiment holds a slot while waiting, retries in a sleep loop, or treats GPU
utilization as permission.

## Implementation phases

1. Build the hermetic agent loop, condition-manifest validator, full per-turn
   request/schema capture, deterministic fixture tools, append-only record file
   and queryable local database, and static result dashboard. Add the deliberate
   contamination self-tests first.
2. Implement one inspection-before-edit fixture and a deterministic oracle.
   Exercise the full runner without a model using a scripted fake provider.
3. Preregister the complete Study A task bank, including development and
   confirmation instances in every shape. Run its pilot. Publish the pilot
   accounting before altering a condition.
4. Freeze a new confirmation registration, schedule, and analysis hash. Run
   confirmation and write a short research note.
5. Reuse the harness for Study B. Do not mix Study B automatic-routing mechanics
   into Study A.

## Decisions that affect the design

1. **Model cohort:** begin only with production's current Qwen snapshot, or
   treat model/version as an explicit second factor from the beginning? The
   former gives a smaller, decisive lab; the latter answers broader questions
   but multiplies the sample plan.
2. **Agent implementation:** the recommendation is a small purpose-built loop
   first. It maximizes control. A one-time compatibility fixture can compare its
   declared affordances with Assist; importing DeepAgents would add framework
   context that becomes another uncontrolled treatment.
3. **Result publication:** should raw prompt/trace artifacts remain local by
   default, with only aggregated tables committed? The recommendation is yes,
   because traces can become large and their value is primarily diagnostic.
4. **Qualitative review:** should the first studies use only deterministic
   artifact outcomes, or include a blinded human interpretation layer? The
   recommendation is deterministic primary outcomes and optional blinded review
   until a real ambiguity demands it.
