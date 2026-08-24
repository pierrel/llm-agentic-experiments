# Durable-promise capability routing v3

Status: registered pilot. No model episode has run in this version.

## Lineage and question

V3 is a clean successor to the preserved exploratory work and to v1 and v2,
whose first scheduled workers both ended before any provider request. Their
private evidence remains immutable at the versioned event records; neither is
baseline evidence and neither is replayed. This cohort tests the same narrow
question: whether one general sentence in grounding's skill description makes
the ordinary web main load grounding before a superficially matching generic
capability when the answer is a fact in the user's records.

`C0` is the exact current grounding description. `C1` changes only its
description by adding: “A question about the user's own date, time, meeting,
deadline, or status needs this skill when the answer comes from their records.”
All other prompt, skill, schema, model, fixture, and runtime inputs are sealed
identically in the bundle.

## Why this successor is necessary

V2's lifecycle had only `launch-intent` and a final provider boundary. It
could establish that no request occurred, but not where setup stopped. V3 adds
non-sensitive checkpoints for descriptor validation, task validation, and
served-model verification before the existing exact provider-request marker.
It is harness observability only: it does not alter model-visible content,
tools, task order, scoring, or either treatment. A new version is required
because the worker implementation is part of the sealed cohort.

## Design and decision rule

The four fresh natural pilot rows, 24 counterbalanced C0/C1 episodes, R/P/A/F
observables, and count-only advance rule are identical to v2. R requires
grounding first, then the context task, a checked exact result before dependent
work, and no earlier user-file/capability work. P requires the requested
post-result `/agent/memory.md` commitment. A requires the local fact in the
answer and no unsupported completion claim. F requires all three.

V3 advances only if C1 has at least two more R and F successes than C0 across
the 12 rows per condition, with no P or A decrease for either lower-conflict
sentinel. It selects no release candidate. Passing requires a separately
registered, unseen confirmation bank and the fixed product regression panel.
Any pre-request infrastructure failure is terminal, retained, and never
silently retried.

The sealed bundle is `bundle.json` with SHA-256
`4fdb9c23fff72a3ab19aaf5611995cc1d8f8f96fb25894fe7ad6253b06ec7d2f`.
