# Design review 0035: exact V8-r3 reproduction

## Lineage

This reproduction preserves the registered design in
`experiments/reach-for-instructions-confirmation-v8-qwen38-current/registration.md`
and the completed report in
`reports/reach-for-instructions-confirmation-v8-qwen38-current.md`. It does not
revise either historical record. It adds a new preregistered execution and
stronger administrative identity checks because an exact reproduction must not
silently inherit a different checkout, runtime, server, or denial classification.

## Authoritative target

The target is exactly the valid, complete, current-profile V8-r3 confirmation at
lightweight tag `reach-for-instructions-confirmation-v8-qwen38-current-r3`,
commit `3ac6975e46f6c217feb8237ca15e4c65eea3065d`, tree
`4754881f77f97dc036ca1bdaa8a568ce45674c94`. Earlier reach confirmations are
invalid, partial, or use a different registered design. Selecting among them by
their observed result is prohibited.

## Preserved experimental design

The reproduction uses the parent's exact 72-trial bundle. This preserves the
hypothesis, G01 handed versus G02 discoverable guidance contrast, 0/900/3,600
inert-line doses, Northridge Labs fixture, one-turn natural user prompt, full
system prompts, provider-request digests, schedule and order, V8-r3 semantic and
ordered-workspace oracle, secondary guide-load measure, Qwen3.8 profile, Assist
revision, inherited runner, 24-terminal batch bound, 900-second break, no
result-based stop, and intention-to-treat handling of every admitted terminal
outcome.

## Reproduction-specific integrity controls

The reproduction adds no model-visible treatment. Its wrapper:

1. Requires a clean checkout of the exact published annotated reproduction tag,
   proves the branch and tag publication once during runtime preparation, and
   binds subsequent checks to the saved proof and immutable local tag rather than
   repeatedly consulting a mutable remote branch.
2. Builds and verifies clean detached local clones of the exact parent and Assist
   commits in a locked private staging directory, then atomically publishes the
   sole fixed canonical-workspace runtime root. The raw cohort,
   attestation inventory, and private sealed capsule also have single fixed child
   paths, so alternate locks or same-ID cohorts cannot be selected.
3. Derives the canonical workspace from the registered worktree's Git common
   directory, pins a minimal parent environment to that `AGENTIC_ROOT`, exact
   coordinator, and `/usr/bin:/bin`, uses only that workspace's production-priority
   gate and events, and prevents the gate's forced working directory or an
   inherited environment from shadowing either clean clone or redirecting admission.
   Git and systemd metadata commands receive fixed minimal environments, excluding
   caller-controlled dynamic-loader variables. The fixed root-owned system Python
   runs through a hash-pinned `-S` launcher with the registered dependency
   directory added explicitly to `PYTHONPATH`;
   a caller-selected virtual environment and its `.pth`/`sitecustomize` startup
   surface never become interpreter inputs.
   When the unchanged parent worker command resets `PYTHONPATH` to its two source
   roots, the launcher restores the descriptor-bound dependency path from the
   wrapper's fixed environment before executing the interpreter.
   The production-thread root is resolved only from the Assist service environment,
   checked against its registered path digest, and passed explicitly to the gate.
   Preparation copies the hash-pinned gate and mode-0600 deployment environment into
   a private read-only worker-workspace snapshot with both content digests fixed.
   Each batch opens first, verifies through, and addresses that snapshot through a
   directory descriptor held by the wrapper. The parent, exact code checkouts,
   launcher, and dependency directory all execute through similarly verified held
   descriptors, including during archive. The inherited parent canonicalizes its descriptor path
   to that same prepared checkout before work; the cooperative same-UID protocol, not
   an adversarial local security boundary, protects it after that inherited step.
4. Attests the interpreter, resolved modules, the full non-extra dependency
   closure rooted at deepagents and langchain-openai, Assist commit/tree, parent
   commit/tree/tag/bundle, llama.cpp commit/tree, running server binary/arguments/
   PID/start identity, and complete model bytes before and after every inherited
   parent batch invocation. Archive separately repeats the registered code,
   interpreter, dependency, environment, and shared-gate checks before its worker.
5. Requires identical attestation bytes across the whole reproduction, including
   the normalized parent environment and hashes of its systemd scope tools.
6. Holds a distinct nonblocking wrapper lock across progress inspection,
   attestation, parent execution, event reconciliation, and cooldown recording;
   the inherited child lock remains separate.
7. Reconciles parent admission records with the exact same-thread event-log byte
   slice from one descriptor-bound inode and requires its ordered,
   second-granularity events to fall within the
   seconds containing the parent invocation's recorded UTC bounds and exact
   admission/outcome count transition. Only a
   corroborated production denial retries; an
   admitted timeout may omit the finish event when the inherited safety bound
   kills the wrapper. Persisted 600-second denial and 900-second terminal-batch
   boundaries are copied into the interval history and enforced before the next
   parent invocation. The exact parent cooldown-file mtime anchors the batch
   boundary's registered 900-second duration; ambiguity quarantines.
8. Validates the exact persisted admission/outcome schemas and semantics rather
   than relying on hash-chain continuity alone.
9. Contains the inherited parent and every descendant in one transient systemd
   scope. A startup handshake keeps the parent payload gated until that exact
   live cgroup is observed. The wrapper proves it empty after normal completion;
   on interruption it atomically kills the complete bound cgroup, reaps the
   launcher, proves the scope empty, and coalesces repeated terminating signals
   until cleanup begins, when they are deferred until quarantine is durable. The
   same signal guard remains active through
   post-run reconciliation. The wrapper refuses
   resume or analysis after any identity, detected request-fidelity, event,
   parent-process, or terminal-count failure.
10. Re-verifies the exact parent, Assist, interpreter, dependency closure, and
   gate before archival. The inherited archive worker uses the same gated,
   killable transient-scope mechanism, and terminating signals quarantine the
   raw cohort only after that child tree is killed and reaped. It verifies and
   copies every per-invocation identity
   and event slice, independently reconstructs secondary metadata from the sealed
   traces and outcomes, requires the parent archive to copy those exact bytes,
   binds the evidence to the run and manifest in reproduction provenance before
   analysis, then archives the fixed capsule evidence and analysis under
   a final self-digested seal. Later interpretive `learning.md` and Assist
   proposal files remain deliberately outside that data seal.

## Analysis and validity boundary

The analysis verifies both immutable capsules and the reproduction's complete
admission/outcome/event witness before emitting the preregistered descriptive
six-cell summaries, within-dose
delivery contrasts, token diagnostics, guide-load process counts with explicit
observed and missing denominators, and pair-position diagnostics. The
reproduction and the uniquely pinned historical run
remain separate. No pooling, significance test, threshold selection, or binary
success criterion is introduced after seeing results.

The server attestation is stronger than the historical bundle, which only bound
the model/profile and weights. This improves execution identification but cannot
retroactively prove the historical run used the newly recorded binary and flags.
That asymmetry is a stated limitation, not a reason to alter either treatment or
the comparator.

The inherited worker persists its captured provider request only after a model
call returns. A provider exception or timeout after request start can therefore
retain the parent terminal outcome without exposing the request for fidelity
verification. Successful returned payloads are verified exactly and detected
drift quarantines the cohort. The ambiguous failure cases remain in the fixed
denominator with fidelity explicitly unobserved; discarding and rerunning them
would break the parent intention-to-treat rule.

The workspace and capsule protocol is cooperative local integrity, not a
cryptographic security boundary against another same-UID process that can rewrite
all files and recompute unkeyed hashes. The immutable runner, exact coordinator,
published registration, private directories, wrapper lock, append-only event
slices, and final seals prevent accidental or ordinary operator substitution.
They do not claim to prove provenance against a malicious local administrator.

## Review decisions before admission

Successive pre-admission reviews found and fixed concrete integrity gaps before
any Qwen episode ran: unbounded preparatory subprocesses, termination windows,
incomplete launcher cleanup, inherited Git/system loader variables, repository-
local URL rewriting, caller virtual-environment startup hooks, opaque review-hash
claims, preparation without the registered coordinator, and the unchanged
parent's removal of the explicit dependency path before nested workers. The
current construction bounds and reaps every preparatory process group, keeps the
full signal guard active, uses fixed minimal metadata environments, runs the
fixed system interpreter with `-S`, embeds and hashes review results in the tag,
coordinator-binds preparation, and restores the descriptor-bound dependency path
inside the fixed launcher.

One adversarial review asked for cryptographic authentication of the public
coordinator UUID against another same-UID process. That finding is declined: the
workspace protocol explicitly defines the UUID as a cooperative operational
binding, not a secret credential or a security boundary against a malicious
local peer. Adding a new secret-authentication system would not make this exact
reproduction more valid within its registered threat model.

## Independent preregistration review

Before any model admission, independent Terra reviewers examine four lenses:

- Scientific validity: exact target, treatment isolation, fixture, prompts,
  schedule, oracle, missingness, stopping, and transfer limits.
- Statistical validity: complete denominators, all reason codes, pair-position
  diagnostics, fixed comparator, no pooling, and no result-dependent decision.
- Harness validity: clean checkouts, import and package resolution, shared-gate
  event corroboration, request fidelity, runtime/server invariants, quarantine,
  capsule verification, and final evidence sealing.
- Minimum adequate setup: no smaller design can answer exact reproduction while
  retaining the parent cohort and integrity requirements; added machinery must
  remain administrative and non-model-visible.

Each accepted review is recorded against the exact preregistration commit and
tree in the effort evidence ledger and retained as a durable review artifact. A
changed commit invalidates those approvals and requires another review. A final
independent Sol design signoff follows Terra convergence. The annotated
registration tag embeds the complete text and SHA-256 of all four accepted Terra
artifacts and the Sol signoff, plus their required model identities and the exact
candidate commit/tree. Runtime registration verification recomputes every hash,
requires an accepted final line, and requires the Sol result to name the digest
of the four embedded Terra approvals. It rejects any missing, non-accepted,
opaque, or non-dependent approval before preparation. No model work begins before
that tag is published.
