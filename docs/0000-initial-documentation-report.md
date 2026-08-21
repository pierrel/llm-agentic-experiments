# Initial repository report

## What is ready

`llm-agentic-experiments` is a separate, no-model research repository for
learning how guidance changes tool-using-agent behavior. It has an initial design
for two initial studies, an operating contract, registration and results
templates, a study registry, an example walkthrough, a glossary, and a small
executable integrity layer. It is intentionally not an Assist branch and it
has made no request to the shared GPU.

The executable layer verifies a locally sealed study bundle, constructs an interleaved and
position-balanced blocked schedule, records every admitted episode as a
reason-coded outcome, and writes a local tamper-evident JSONL hash chain. GPU
admission denials are kept as administrative events, not model failures. It
rejects altered bundles, duplicate records, post-request failures disguised as
infrastructure faults, and a schedule with missing records. It also rejects
undeclared condition differences and condition labels in a qualitative-review
packet. Before model use, the runner must bind the bundle digest to an immutable
git commit/tag; the current local hash detects edits but is not by itself a
historical archive.

## Documentation inventory

- `README.md` explains scope, non-negotiable controls, and the planned code
  layout.
- `AGENTS.md` is the operating contract: preregistration, review, integrity
  self-tests, raw-data boundaries, and shared-GPU admission.
- `docs/0001-agentic-guidance-experiments.md` is the program design. Study A is
  a 2×2 repetition/locality experiment. Study B compares chosen progressive
  guidance with fixture-owned automatic delivery as a deliberately bundled
  system-policy intervention.
- `docs/0002-study-registration-template.md` locks each study before model
  results, including its unit, outcome, sample rule, and ordinary-language
  interpretation.
- `docs/0003-results-report-template.md` makes all scheduled trials,
  primary-versus-secondary outcomes, prompt audits, and limits visible.
- `docs/0004-initial-design-review.md` records the scientific-integrity,
  statistical, agentic-harness, and plain-English reviews and their resolutions.
- `docs/example-study-walkthrough.md` shows one invented trial from request to
  tool trace to automatic score.
- `docs/glossary.md` defines the recurring vocabulary briefly.
- `docs/study-registry.md` is the append-only study-version index.

## How to interpret the future evidence

The model will never be allowed to “win” because a condition has extra tools,
a different fixture, a different decoding setup, an undeclared routing decision, or
an excluded timeout. A confirmation result applies only to the preregistered
model snapshot, agent loop, task bank, and decoding setting. A promising pilot
is a reason to lock a new confirmation cohort, never evidence to merge a prompt
into Assist.

## Verification and review

The first local harness checks pass with `python -m unittest discover -s tests
-v`: fourteen tests cover study-bundle tampering, seed policy, block scheduling,
undeclared condition differences, label leakage, record integrity, a finalized
record seal, missing records, incorrect infrastructure-invalid classification,
admission retries/restart recovery that would change registered order,
collision-safe trial accounting, and unbalanced manual schedules. `compileall`
and `git diff --check` also pass.
The four required design lenses found material issues in the initial design;
every one was incorporated before this report.

No deferred product defect exists. The intentionally deferred work is the
real-model runner and analysis/report UI, because those must be built against a
specific registered study and obey the same sealed interfaces.
