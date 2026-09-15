# Exact reproduction of reach-for-instructions V8-r3, r3

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
The separately registered reproduction r1 is also ineligible: it quarantined
after its first batch when final scope verification raced collection of the
already-finished cgroup, before after-identity and event attestations. R2 was
registered to start a new cohort, but its candidate became administratively
stale before tagging or model admission when its coordinator and shared gate
changed. R1 is retained without interpretation, r2 remains unexecuted, and r3
starts a fresh cohort without using outcome content from either reproduction.

The reproduction tests the same hypothesis without changing its treatment,
fixture, prompts, schedule, oracle, harness, or model profile. It is reported as
a new execution and never pooled with the parent result. The exact content of
this registration, the administrative wrapper, and the locked analysis is bound
by `manifest.json`. Before any model request, the clean registration checkout
must equal the published annotated tag
`reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r3`
and the published branch `reach-experiment-reproduction-v3` must point to that
tag's commit. The commit and tree reached by the annotated tag are the authority;
the names are only discovery handles. Runtime preparation makes this publication
check once, saves its self-digested proof inside the private runtime root, and
subsequent pre/post attestations require that proof plus the still-clean local
tagged checkout. They do not depend on a later mutable branch lookup.
The annotated tag message is canonical JSON binding the exact candidate commit,
tree, coordinator, and the complete accepted scientific, statistical, harness,
and minimum-setup Terra review artifact texts plus the final Sol design-signoff
artifact text. The runner recomputes every artifact hash, requires each result to
end in `ACCEPTED`, and requires the artifact itself to name the exact candidate
commit/tree, coordinator, lens, reviewer model, accepted disposition, and a
substantive summary exactly once; conflicting or duplicate identity fields are
rejected. It also requires the Sol artifact to name exactly once the digest of
the four embedded Terra approvals before preparation. The tag message bytes must be
exactly one canonical JSON record plus its final newline; surrounding whitespace
is rejected. The tag object is therefore the durable artifact container and
executable review-admission gate rather than an opaque assertion that external
artifacts exist.

Execution is bound to the registered immutable coordinator identity
`01a04877-df08-7401-aeb5-91fdee52c9b0`. A different `CODEX_THREAD_ID` cannot
start or resume this cohort.

There is exactly one prepared runtime and one raw cohort. The runtime root is the
canonical shared workspace child
`.coordination/reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r3`;
its parent and Assist checkouts, raw output, runtime attestations, and capsule use
the fixed relative paths in `manifest.json`. Preparation builds and verifies a
private staging directory under a nonblocking lock, atomically publishes it at
the sole canonical path, and refuses an alternate or existing root. An interrupted
or failed preparation therefore cannot strand a partial canonical runtime. Batch
and archive commands reject alternate or symlinked paths before touching
cohort state. The fixed raw path makes the wrapper lock global to this
reproduction and prevents selecting among parallel same-ID cohorts. The sealed
capsule is first built at its fixed private runtime path so archival does not
dirty the registered checkout.

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

Every returned pass or artifact-failure trace must contain both registered
secondary observations. A present result object is likewise required to contain
a Boolean guide-load observation and a nonnegative integer input-token count,
or `null` only when token usage was unavailable. Only timeout, provider-error,
or infrastructure-invalid traces may omit the result object and retain both
observations as missing.

For every worker payload that returns, the captured first provider request must
equal its sealed request or the whole reproduction is quarantined. The inherited
worker writes that capture only after `agent.invoke` returns. An admitted
provider exception or timeout after the request-start marker can therefore end
without a payload that exposes the actual request. Its request-fidelity status
remains unobserved: it is neither called verified nor inferred to have drifted,
and its parent terminal outcome remains in the denominator. Restarting the
cohort on that outcome would violate the inherited intention-to-treat rule and
could select on condition or context. The locked analysis reports verified and
unobserved request-fidelity counts for every cell.

## Execution, stopping, and missingness

The unchanged V8-r3 runner executes from a private clean detached checkout of
the parent commit. Assist executes from a separate private clean detached
checkout at commit `54b7b1049f43b86a0907203872b7b9c9ae8fb9a4`, tree
`e3df40b30613c94a6d3455e920748b4c155a84a1`. The fixed root-owned system
interpreter is used through the registered `-S` launcher with
`PYTHONSAFEPATH=1`, `PYTHONNOUSERSITE=1`, and a `PYTHONPATH` containing the two
source roots plus the registered dependency tree. The wrapper verifies exact imported files and every
installed file listed in each distribution RECORD in the non-extra dependency
closure rooted at deepagents and langchain-openai. Declared RECORD hashes must
match, and the actual bytes of both hashed and unhashed entries feed the closure
identity. That closure includes the LangChain/LangGraph support packages, OpenAI
client, HTTP stack,
Pydantic, and their declared runtime dependencies; its complete package list
and identity digest are fixed in `manifest.json`. The wrapper gives the inherited
parent a fixed minimal environment: the canonical `AGENTIC_ROOT`, exact coordinator
thread, `/usr/bin:/bin` path, fixed localhost proxy bypass, and the registered
Python isolation variables. This prevents an inherited caller environment from
redirecting the shared gate or its interpreter. The gate receives an explicit
production-thread directory derived from the Assist service environment whose
path digest is fixed in `manifest.json`; caller variables and later worker
environment loading cannot select another admission-status namespace. The wrapper replicates the inherited
worker's deployment-environment loading from a mode-0600 source and requires its non-secret model
endpoint to remain exactly `http://127.0.0.1:8000/v1` without recording secret
environment values. The normalized fixed path and workspace root, plus hashes of
the systemd scope tools used to contain the parent process tree, are part of every
runtime identity attestation.
Git and systemd metadata subprocesses receive fixed minimal environments rather
than inherited loader, helper, proxy, or configuration variables. Execution uses
the one path-hash-pinned root-owned system Python through a hash-pinned launcher
that always supplies `-S`. The registered dependency-tree directory is opened and
held independently, then added explicitly to `PYTHONPATH`. It is not selected as
a virtual environment or processed as a site directory, so its `.pth`,
`sitecustomize`, and `usercustomize` files cannot execute at startup.
The public administrative CLI first re-executes itself through that same fixed
system Python with `-S` and a complete minimal environment before importing any
experiment, harness, or installed dependency module. A forged clean-entry marker,
different interpreter, enabled site startup, or extra environment field fails
closed.
The inherited exact parent replaces `PYTHONPATH` with its two source roots before
each worker. The pinned launcher restores the descriptor-bound dependency path
from the wrapper's fixed environment before starting system Python with `-S`.
At preparation, the exact gate and deployment environment are copied into a private
worker-workspace whose directories and gate are mode 0500 and whose environment is
mode 0400. The manifest fixes both file digests. Each invocation opens the snapshot,
exact parent checkout, exact Assist checkout, and interpreter environment first,
then verifies all identities through those descriptors. The inherited parent uses
only `/proc/<wrapper>/fd/<descriptor>` references held open through the batch. The
gate still reads canonical coordination state through the fixed `AGENTIC_ROOT`;
only executable, source, and configuration pathname resolution is descriptor-bound.
The inherited parent canonicalizes its parent-checkout descriptor to the same
prepared checkout before execution. Preventing a malicious same-UID process from
rewriting that inode afterward is outside this cooperative protocol's stated
security boundary. Archive repeats the same open-first descriptor verification.
The inherited archive worker also runs in a transient scope using the same gated
startup and whole-cgroup cleanup mechanism. Terminating signals during any part
of the archive transaction become cleanup-bearing interruptions; the worker tree
is killed and reaped before lock release, and the raw cohort is quarantined.
After scope binding and gated release, the complete parent payload has an
18,000-second limit and the archive payload a 900-second limit. Expiry uses the
same whole-cgroup kill/reap/quarantine path; it never creates or retries a scored
outcome.
Every preparatory Git or environment-attestation subprocess has a separate
900-second process-group deadline. Expiry kills that complete group and boundedly
reaps its launcher before preparation fails or the raw cohort is quarantined;
the local systemd metadata probes use a ten-second deadline through the same helper.

Every model-capable worker remains inside the shared workspace
`tools/agentic resource run llm` gate. One wrapper invocation admits at most 24
terminal episodes. Any invocation that records 24 terminal episodes while the
schedule remains incomplete keeps the parent's recorded 900-second cooldown.
There is no result-based stop and no replacement of admitted outcomes.
The invocation that records the 72nd outcome verifies the parent admission and
outcome seals plus the exact report and trace digests before returning
`complete`. After all 72 outcomes and their existing runtime evidence verify,
another `run-batch` re-verifies the same final evidence without a fresh server
attestation, parent launch, or empty evidence interval.
One separate nonblocking reproduction lock covers the complete wrapper
transaction from persisted-progress inspection through before/after identity,
parent execution, event reconciliation, and cooldown recording. It does not
reuse the inherited parent output lock.
The inherited parent and every descendant, including workers that start their own
sessions, run inside one transient user-systemd scope. A pipe handshake prevents
the parent payload from starting until the wrapper observes and validates that
exact live cgroup. Normal completion requires the previously bound scope to be
empty. A missing cgroup or the cgroup filesystem's `ENODEV` response is accepted
only after the bound launcher has returned because the kernel cannot remove a
cgroup that still has members. Any other membership-read failure is rejected.
Wrapper interruption kills the complete bound scope through the cgroup's
atomic `cgroup.kill` control, reaps its launcher, and verifies no scope member
remains before quarantine and lock release. If that bound control has vanished,
cleanup proceeds only when the membership interface also returns `ENOENT` or
`ENODEV`, proving that the kernel collected the cgroup; a readable cgroup without
its atomic control fails closed. One signal guard remains active
through child cleanup and post-run reconciliation. Repeated signals are coalesced
until cleanup begins, then kernel-level deferral protects the kill, reap, and
quarantine sequence until it is durable. A failure before binding can stop only
the still-gated bootstrap and can never release the parent payload.

The wrapper hashes that exact shared gate before and after every parent batch
invocation and once more before archive, and opens its sibling
`.coordination/events.jsonl` once before execution, then reads the
appended evidence from that same inode. The prior prefix is fingerprinted and all
file hashes are streamed in 1 MiB chunks. Each appended event record is at most
1 MiB, and the complete invocation slice is limited to 16 MiB and 16,384 records;
exceeding a bound is malformed event evidence and quarantines the cohort. A different
tool or caller-selected event log cannot authorize an admission or retry. The
shared workspace itself is derived from the registered worktree's Git common
directory. The wrapper derives its source checkout from its own imported module,
requires `--root` to be that exact lexical path, and requires registered SHA-256
digests of the canonical workspace and Git-common absolute paths. It strips
caller-supplied `GIT_*` repository/configuration overrides from every fixed
`/usr/bin/git` command and disables local fsmonitor, untracked-cache, and hook
execution. Those safe Git variables are also fixed in the inherited parent and
worker environment after deployment-environment loading. A caller-supplied
copied workspace cannot substitute its own lock or event namespace.

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
the seconds containing those bounds. The reader retains every event for this
coordinator thread and the `llm` resource so bounded validation rejects an
unexpected event name rather than omitting it. The wrapper persists a 600-second
`not_before` record after each
corroborated denial and inherits the parent's persisted 900-second boundary
after each full incomplete batch. For a batch boundary, the wrapper attests the
parent file's exact mtime and requires `not_before - 900` to fall within the
invocation and no more than one second before that atomic write. It copies both
applicable boundaries into the immutable interval history, requires the live
files to match that history, refuses an earlier attempt, and verifies the same
cadence in the final capsule. Admission
and outcome records must also retain the exact parent schemas, scheduled trial
identity, field types, and outcome semantics in addition to valid hash chains.
Every non-infrastructure outcome must carry the parent's request-start marker;
an infrastructure-invalid outcome must not carry it.
Every persisted JSON value is decoded without duplicate members, non-standard
numeric constants, or a numeric token that decodes to a non-finite value. Every
runtime interval must contain at least one admission;
an empty interval can never attest a completed or resumed invocation.
Before any resumed launch, nonempty persisted admissions or outcomes must have
a complete corresponding runtime-attestation interval prefix. When the latest
admission is a denial, its cooldown must bind that exact latest admission count
and trial; an older valid cooldown cannot authorize another attempt. The wrapper
also rescans all persisted outcomes for provider-request fidelity failures before
admission rather than checking only outcomes returned by the current invocation.
Archive repeats the live batch- and denial-cooldown reconciliation against the
complete attestation history before copying or sealing the cohort.
Any other unadmitted failure, nonzero parent invocation, malformed event slice,
detected request-fidelity error, unexpected episode count, registration/import/dependency/
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
process start identity are captured before and after every parent batch invocation,
and that exact process, in the same network namespace as the wrapper and workers,
must own the unique IPv4 listener at `127.0.0.1:8000`.
The 17,559,178,144-byte model and server binary are re-hashed each time, and all
identity attestation bytes must remain identical across the execution.

## Locked analysis and historical comparator

Analysis begins only after all 72 scheduled admissions and outcomes have valid
final seals, all trace/report hashes verify, the capsule `run.json` self-digest
binds its trial metadata, and the runtime attestation inventory is complete.
Trial metadata must contain both secondary keys; pass and artifact-failure rows
require a Boolean guide-load observation.
Before calling the parent archive, the wrapper strictly parses the live evidence,
requires `output/bundle.json` to match both the registered parent bundle digest
and exact file SHA-256, and rescans every persisted outcome for a terminal
provider-request fidelity failure.
Before calling the parent archive, the wrapper independently recomputes the exact
secondary metadata bytes from the raw trace bodies and sealed outcomes. The parent
archive must verify those trace hashes and copy metadata that exactly matches the
independent reconstruction; mutable raw metadata cannot become sealed evidence.
Immediately before the parent archive command, the wrapper re-verifies the exact
parent and Assist checkouts, interpreter, imported modules, full dependency
closure, environment, and shared gate. An archive-stage reproduction-integrity
failure permanently quarantines the raw cohort.
Before locked analysis summarizes an outcome, the wrapper copies the verified attestation
inventory into the capsule and writes a self-digested provenance record binding
every copied file, the capsule run record, manifest, and coordinator identity.
The final evidence-seal inventory structurally excludes its own root
`reproduction-seal.json` to avoid self-reference. Its only content exclusions
are root-level `learning.md` and `assist-roadmap-proposal.md`, which are later
interpretation. Identically named files below an evidence subdirectory remain
sealed.
The only historical comparator is the preregistered parent capsule
`results/reach-for-instructions-confirmation-v8-qwen38-current-r3/`, pinned by
its run-file SHA-256
`d073940d4e3fc32efa0519a2956e27e6164a44ffa005d30fb73baa05fdc82676`.

The locked analysis reports the two runs separately. For each of six cells it
reports denominator, pass count/rate, every reason-code count, guide-load count/
observed denominator, missing count, observed-case rate, input-token
values and range, and outcome counts by within-pair position.
It also reports the count of returned-payload episodes whose first request was
verified and admitted terminal episodes whose inherited failure path left request
fidelity unobserved.
It reports G02 minus G01 pass-rate percentage points by dose. It does not pool
runs, select another comparator, calculate an unregistered p-value or context
threshold, or apply a binary replication-success rule. Interpretation remains
specific to this task, model, profile, and harness.
