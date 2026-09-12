# Exact reproduction of reach-for-instructions V8-r3

## Authority and purpose

This is a separate exact reproduction of the only valid, complete, current-profile
reach-for-instructions confirmation: `reach-for-instructions-confirmation-v8-qwen38-current-r3`.
The authoritative parent is the lightweight tag of that name at commit
`3ac6975e46f6c217feb8237ca15e4c65eea3065d`, tree
`4754881f77f97dc036ca1bdaa8a568ce45674c94`. Its sealed bundle digest is
`13f853ad3c04150741c8a94a8f4dd8afb5c2eeeeb7a4666b2ead5a0d12cf5044`
and its bundle-file SHA-256 is
`4bf6462dd04645a239227c9c4182339c7e2dc1218839cae2b4c8d9cc3d25666d`.
Earlier confirmations are invalid or incomplete and are not eligible alternatives.

The reproduction tests the same hypothesis without changing its treatment,
fixture, prompts, schedule, oracle, harness, or model profile. It is reported as
a new execution and never pooled with the parent result. The exact content of
this registration, the administrative wrapper, and the locked analysis is bound
by `manifest.json`. Before any model request, the clean registration checkout
must equal the published annotated tag
`reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r1`
and the published branch `reach-experiment-reproduction-v2` must point to that
tag's commit. The commit and tree reached by the annotated tag are the authority;
the names are only discovery handles. Runtime preparation makes this publication
check once, saves its self-digested proof inside the private runtime root, and
subsequent pre/post attestations require that proof plus the still-clean local
tagged checkout. They do not depend on a later mutable branch lookup.

Execution is bound to the registered immutable coordinator identity
`01a09689-f137-7cf1-a5c0-f32e7537fefa`. A different `CODEX_THREAD_ID` cannot
start or resume this cohort.

## Hypothesis, conditions, and prompt sequence

The unchanged question is whether this procedure-heavy natural equipment-return
task completes more often when the agent discovers and loads a matched guide
than when the full procedure is already in system context.

Each episode has exactly one user turn:

> Please prepare a compact JSON handoff for the Northridge Labs equipment-return
> case from the workspace material. Include the case ID, verified equipment ID,
> return status, approval status, next owner, next action, and the remaining
> uncertainty.

Both conditions receive the fixed `load_skill(name: string)` schema and the
normal Deep Agents filesystem/TODO tools. G01 receives the full procedure in
system context and no guide catalog entry:

> For an equipment-return handoff, first inventory the workspace. Read every
> source record before writing. Preserve source records. Reconcile only supported
> facts, identify unresolved conflicts, and create one structured handoff.

G02 receives only this catalog entry in system context:

> Available procedural guide: prepare-equipment-return. Use it when a request asks
> you to consolidate an equipment-return case into a handoff.

The G01 procedure and G02 catalog entry follow the shared sentence `You work in
a local workspace.` G02 can obtain the procedure only through the exact call
`load_skill("prepare-equipment-return")`. At each dose, both conditions receive
the same deterministic inert prefix. C-low has 0 lines, C-medium 900 lines, and
C-high 3,600 lines. Every line has the parent's exact form and numbering.

## Fixture, schedule, and unit

The fixture is the unchanged five-file Northridge Labs workspace for case
NL-9127 and equipment EB-507. It identifies kit K-31, conditionally approved
closure after an unconfirmed intake photo, operations owner Rowan, and the
unresolved S-4 versus S-4B label. Its bundle digest is
`a4415715c20ebcea80f392b76d629cb9a40371a93dedcc7104969d3dfa63998d`.

One unit is one fresh private Deep Agents episode. The exact parent schedule has
72 episodes: 12 for every G01/G02 by C-low/C-medium/C-high cell. It retains the
parent's opaque trial IDs, intact within-dose condition pairs, exact order, and
randomization seed `20260913`. Trial seeds label schedule entries only; the local
provider exposes no sealed generation-seed control.

## Outcomes and oracle

The unchanged primary outcome is one new valid JSON handoff that is grounded in
the fixed fixture, preserves all source files, inventories before reading, reads
all five source records before any write, and writes only after those reads. The
handoff must identify NL-9127, EB-507, conditional approval with the intake photo
still pending, Rowan, confirmation of the K-31 intake photo before closing
EB-507, and the unresolved relationship among S-4, S-4B, and K-31. The exact V8-r3
condition-blind calibration and scorer decide acceptance.

The unchanged secondary process measure is whether the exact named guide is
loaded before the first source-record read. It is computed from the trace even
when the primary artifact fails; a timeout or interrupted trace that cannot
expose the measure remains missing rather than being classified as no load. The
execution retains every admitted terminal result with the parent reason codes,
plus actual first-provider-request input tokens when available.

## Execution, stopping, and missingness

The unchanged V8-r3 runner executes from a private clean detached checkout of
the parent commit. Assist executes from a separate private clean detached
checkout at commit `54b7b1049f43b86a0907203872b7b9c9ae8fb9a4`, tree
`e3df40b30613c94a6d3455e920748b4c155a84a1`. The deployed Assist interpreter is
used with `PYTHONSAFEPATH=1`, `PYTHONNOUSERSITE=1`, and a `PYTHONPATH` containing
only those two source roots. The wrapper verifies exact imported files and every
installed file listed in each distribution RECORD in the non-extra dependency
closure rooted at deepagents and langchain-openai. Declared RECORD hashes must
match, and the actual bytes of both hashed and unhashed entries feed the closure
identity. That closure includes the LangChain/LangGraph support packages, OpenAI
client, HTTP stack,
Pydantic, and their declared runtime dependencies; its complete package list
and identity digest are fixed in `manifest.json`. The wrapper replicates the
inherited worker's mode-0600 deployment-environment loading and requires its
non-secret model endpoint to remain exactly `http://127.0.0.1:8000/v1` without
recording other environment values.

Every model-capable worker remains inside the shared workspace
`tools/agentic resource run llm` gate. One wrapper invocation admits at most 24
terminal episodes. Any invocation that records 24 terminal episodes while the
schedule remains incomplete keeps the parent's recorded 900-second cooldown.
There is no result-based stop and no replacement of admitted outcomes.
One separate nonblocking reproduction lock covers the complete wrapper
transaction from persisted-progress inspection through before/after identity,
parent execution, event reconciliation, and cooldown recording. It does not
reuse the inherited parent output lock.

The wrapper hashes that exact shared gate before and after every invocation and
accepts evidence only from its sibling `.coordination/events.jsonl`. A different
tool or caller-selected event log cannot authorize an admission or retry. The
shared workspace itself is derived from the registered worktree's Git common
directory; a caller-supplied copied workspace cannot substitute its own lock or
event namespace.

A production-priority denial is administrative missingness and retries the same
trial only when all three facts agree: the parent admission is false with the
exact gate denial text, the exact post-launch byte slice of the shared event log
contains one same-thread `production_admission_denied`, and it contains no
same-thread LLM start for that attempt. The coordinator retries on the required
ten-minute cadence without changing the trial. Every admitted episode must
instead match one same-thread `resource_started` and `resource_finished` pair;
a parent-recorded timeout may lack the finish event because the inherited runner
terminates the admitted process group at its safety limit. Each retained event
slice records the parent invocation's UTC bounds and exact admission/outcome
counts before and after it; all resource events must be ordered and fall within
those bounds. The wrapper persists a 600-second `not_before` record after each
corroborated denial and the parent's 900-second boundary after each full
incomplete batch. It copies both applicable boundaries into the immutable
interval history, requires the live files to match that history, refuses an
earlier attempt, and verifies the same cadence in the final capsule. Admission
and outcome records must also retain the exact parent schemas, scheduled trial
identity, field types, and outcome semantics in addition to valid hash chains.
Any other unadmitted failure, nonzero parent invocation, malformed event slice,
request-fidelity error, unexpected episode count, registration/import/dependency/
model/server drift, or before/after attestation mismatch quarantines the entire
reproduction. It cannot resume or be analyzed; a fresh registered reproduction
would be required.

## Model and server identity

The unchanged model profile is `Qwen3.8-27B-UD-Q4_K_XL.gguf`, weights SHA-256
`3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`,
temperature 0.1, reasoning enabled, 131,072-token server context, no client
`max_tokens` field, 600-second worker timeout, provider-default cache, and a
20-turn recursion safety bound. The harness remains deepagents 0.6.1,
langchain 1.3.1, and langgraph 1.2.0.

The original bundle did not bind its llama-server binary or complete launch
arguments. This reproduction adds a non-treatment integrity attestation of the
observed server: llama.cpp source commit
`192067b72d1b7a3653b3f0c59190303b18596637`, clean tree
`5f17bef5a18d0da06d59744b46b8f2203d889c83`, server binary SHA-256
`b97a9b61c878c52f1025dbe3f3494cc44e9611449cfeab4a0f1a25c84dea7f3a`,
and the normalized launch arguments in `manifest.json`. The actual PID and
process start identity are captured before and after every bounded invocation.
The 17,559,178,144-byte model and server binary are re-hashed each time, and all
identity attestation bytes must remain identical across the execution.

## Locked analysis and historical comparator

Analysis begins only after all 72 scheduled admissions and outcomes have valid
final seals, all trace/report hashes verify, the capsule `run.json` self-digest
binds its trial metadata, and the runtime attestation inventory is complete.
Immediately before the parent archive command, the wrapper re-verifies the exact
parent and Assist checkouts, interpreter, imported modules, full dependency
closure, environment, and shared gate. An archive-stage reproduction-integrity
failure permanently quarantines the raw cohort.
Before locked analysis summarizes an outcome, the wrapper copies the verified attestation
inventory into the capsule and writes a self-digested provenance record binding
every copied file, the capsule run record, manifest, and coordinator identity.
The only historical comparator is the preregistered parent capsule
`results/reach-for-instructions-confirmation-v8-qwen38-current-r3/`, pinned by
its run-file SHA-256
`d073940d4e3fc32efa0519a2956e27e6164a44ffa005d30fb73baa05fdc82676`.

The locked analysis reports the two runs separately. For each of six cells it
reports denominator, pass count/rate, every reason-code count, guide-load count/
observed denominator, missing count, observed-case rate, input-token
values and range, and outcome counts by within-pair position.
It reports G02 minus G01 pass-rate percentage points by dose. It does not pool
runs, select another comparator, calculate an unregistered p-value or context
threshold, or apply a binary replication-success rule. Interpretation remains
specific to this task, model, profile, and harness.
