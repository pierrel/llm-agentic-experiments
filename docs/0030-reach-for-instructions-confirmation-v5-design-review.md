# Reach-for-instructions confirmation V5 seed-record correction

V4 stopped after 22 admissions because its sealed registration recorded V2's
randomization seed instead of the seed that generated its schedule. V5 starts a
fresh cohort and changes only that provenance defect.

## Scientific integrity

The V5 wrapper binds `RANDOMIZATION_SEED` both while creating the schedule and
while rewriting the sealed registration before its bundle is written. V4's raw
chain remains local audit evidence, not a source of conditions, scoring, or
sample replacement. The fixture, opaque delivery labels, prompt rendering, and
provider-request fidelity contract remain fixed.

## Statistical rigor

V5 retains 12 fresh episodes in each delivery-by-context cell, 72 total, with
fresh interleaving seed `20260905`. The fixed sample, administrative admission
retry policy, 24-terminal-episode batches, and all-outcomes analysis are
unchanged. The registration can now identify the actual randomization used.

## Agentic harness fit

V5 reuses the same reasoning-disabled Qwen3.8 Deep Agents filesystem loop,
one fixed load_skill tool, private fixture, deterministic semantic oracle, and
exact first-provider-request check as V4. No agent capability, task fact, or
treatment wording changes.

## Minimum adequate setup

Correctly recording the schedule seed is the smallest possible change that
makes the cohort reproducible. Reusing V4 records or adding a model, task,
skill, judge, or additional context factor would not repair that defect and
would expand the causal design.
