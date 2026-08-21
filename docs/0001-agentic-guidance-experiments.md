# Design 0001: controlled agentic-guidance experiments

## Purpose

Measure how model-facing guidance changes an agent's observable behavior. The
research question is not whether a sentence sounds clearer to us. It is whether
the same small model chooses the intended affordance, produces the requested
artifact, and avoids unwanted work under a controlled agentic loop.

This laboratory is separate from Assist so exploratory prompts, fixtures, and
negative findings cannot quietly become product behavior.

## Shared experimental model

Every study uses a minimal agent with:

- a system prompt and one natural user request;
- a stateful virtual workspace with deterministic files;
- tools for read, write, list, execute-like deterministic transforms, and a
  `load_skill(name)` progressive-disclosure tool;
- optional specialist-task tools with canned, typed results;
- a bounded tool loop, complete trace, and deterministic final artifact oracle.

The harness owns the loop and fixtures. A study supplies only its treatment
manifest, task matrix, and oracle. It must capture the exact provider request,
tool schemas, tool results, model/version/configuration, fixture digest, random
seed, condition, and final trace for every trial.

No external network, repository, clock, user data, or live Assist state belongs
in a first-study fixture. Synthetic tool data uses arbitrary names and values so
model memory cannot answer from a familiar fact.

## Study A: repetition, locality, and steerability

### Question

Does concise operational guidance repeated at the decision point improve an
agent's ability to choose and complete a required tool-mediated workflow?

### Hypothesis

For tasks that require loading a skill and then taking a particular tool path,
a consistent local restatement in the loaded skill will increase task success
and correct-path selection compared with the same rule expressed only in the
system prompt.

### Conditions

The condition manifests are token-budget matched. All conditions have the same
tools, skill catalog description, user request, fixture, decoding settings, and
approximately equal composed system-context length. Neutral operational text,
never instructions, pads a shorter condition if necessary.

1. **System-only:** one concise operational rule in the system prompt; the
   loaded skill names the goal but not the action.
2. **Local repeat:** identical system rule plus a concise, semantically
   identical restatement immediately beside the relevant loaded-skill step.
3. **Control repeat:** identical system rule plus equal-length, task-relevant
   but non-operational skill text. This separates locality from raw extra text.

The primary outcome is a deterministic success artifact. Secondary outcomes
are correct first consequential tool call, unwanted-tool count, tool-call
latency, and truthful final response. The treatment is not allowed to name a
fixture file, test, oracle, or expected tool argument.

The initial task matrix has at least four different workflow shapes: local
inspection before edit, report-backed specialist handoff, deterministic
calculation after a fact lookup, and bounded multi-entity delegation. A result
that appears in only one shape is a task-specific observation, not a general
prompting conclusion.

## Study B: chosen progressive guidance versus automatic delivery

### Question

When the same guidance is needed, is it more effective for an agent to request
it through `load_skill`, or for the host to provide the body automatically at
the equivalent point in the turn?

### Conditions

1. **Chosen:** the skill catalog exposes the guidance. The agent must call
   `load_skill`; its returned body is appended as the next model context.
2. **Automatic:** the same exact body is appended at the point where a routing
   policy identifies the same task shape. The model sees no skill-loading tool
   result and receives no extra capabilities.
3. **Automatic neutral control:** an equal-size non-operational body is appended
   at that point. This distinguishes delivery from simply adding context.

The automatic route is determined by a fixture-owned, deterministic task label,
not by a model classifier. It is deliberately invisible to the user and oracle.
For comparable traces, the chosen condition gets a dedicated model step after
the load result; automatic conditions get the same extra model step after the
injection. Thus the experiment does not mistake one less turn for better
guidance.

Primary outcomes are final artifact success and correct affordance selection.
Secondary outcomes include tool calls, model turns, latency, prompt size, and
the rate of unnecessary skill loads. The analysis reports both outcome quality
and interaction cost. Automatic delivery is not presumed superior merely
because it saves a model decision.

## Scientific controls and statistical plan

Each study gets a preregistration manifest before its first model run. It fixes:

- hypotheses, conditions, primary and secondary outcomes, task matrix, model
  snapshot, decoding parameters, timeouts, exclusions, and analysis code hash;
- randomization: a blocked, seeded schedule pairing each task and replicate
  across conditions, with randomized within-block order;
- sample plan: pilot N=10 per task-condition to estimate variance, then a
  preregistered confirmation sample sized from the pilot without reusing pilot
  labels for the confirmatory p-value;
- inference: effect sizes and confidence intervals first; a mixed-effects
  logistic model with task as a random intercept for binary success; paired
  comparisons within task/replicate blocks; false-discovery control across
  secondary outcomes;
- stopping: no stopping for favorable intermediate results. GPU availability can
  pause a run but cannot select or discard individual trials.

The runner writes one immutable JSON record per trial and a manifest that lists
every scheduled trial, including failures and timeouts. It stores condition IDs
instead of treatment names in the trace; the analysis join unlocks labels only
after deterministic scoring. Prompt snapshots are captured before runs and
diffed mechanically to prove the treatment factor.

## Contamination and bias guards

- Fresh process, fresh conversation, fresh fixture directory, and fresh tool
  state per trial.
- Canned tool results contain no condition name, instruction-shaped text, or
  source path outside the fixture.
- Shared prompt fragments are content-addressed. The runner refuses a condition
  if undeclared prompt, tool-schema, fixture, or decoding differences appear.
- User prompts are natural outcome requests. Architecture, tool, skill,
  routing, and assertion language is prohibited unless the study explicitly
  labels a row as capability coverage.
- Deterministic oracles execute before a blinded qualitative reviewer sees a
  trace. Reviewer packets replace condition names with opaque IDs.
- Development and confirmation task sets are disjoint. Prompt changes after
  development require a new preregistration and a new confirmation cohort.

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

1. Build the hermetic agent loop, condition-manifest validator, prompt/schema
   capture, deterministic fixture tools, JSONL/SQLite record store, and static
   result dashboard.
2. Implement one inspection-before-edit fixture and a deterministic oracle.
   Exercise the full runner without a model using a scripted fake provider.
3. Preregister and run Study A pilot. Review traces blind, then publish the
   pilot analysis before altering a condition.
4. Add the remaining Study A task shapes, run confirmation, and write a short
   research note.
5. Reuse the harness for Study B. Do not mix Study B automatic-routing mechanics
   into Study A.

## Decisions that affect the design

1. **Model cohort:** begin only with production's current Qwen snapshot, or
   treat model/version as an explicit second factor from the beginning? The
   former gives a smaller, decisive lab; the latter answers broader questions
   but multiplies the sample plan.
2. **Agent implementation:** use a small purpose-built loop, or adapt
   DeepAgents as a pinned dependency? A purpose-built loop maximizes control;
   DeepAgents maximizes applicability but adds framework context that must be
   captured and controlled.
3. **Result publication:** should raw prompt/trace artifacts remain local by
   default, with only aggregated tables committed? The recommendation is yes,
   because traces can become large and their value is primarily diagnostic.
4. **Qualitative review:** should the first studies use only deterministic
   artifact outcomes, or include a blinded human interpretation layer? The
   recommendation is deterministic primary outcomes and optional blinded review
   until a real ambiguity demands it.
