# Reach-for-instructions confirmation V3: Qwen3.8

## Decision

Run a new 72-episode Qwen3.8 confirmation only after the standalone
access-transition oracle calibration gate passes. Do not resume V2 or pool its
episodes: it is invalid measurement evidence, not an incomplete cohort.

## Why this is a distinct run

The model is a first-class experimental setting. Qwen3.8 changes the weights,
served model identity, and response surface even though the harness, task,
context doses, delivery intervention, reasoning setting, decoding, and tools
remain fixed. The V3 bundle therefore records the Qwen3.8 GGUF SHA-256 and a
fresh randomization seed, while making no model-transfer conclusion from V2.

## Minimum valid design

The task remains the smallest demonstrated setting with a delivery signal:
handed guidance is in system context; reached guidance is returned by the
single named skill only when the agent requests it. Both use a private virtual
filesystem and the identical task records. The natural user request does not
direct tool use or describe the oracle. Three predeclared inert context doses
test whether the effect changes as ordinary context increases.

The only validity change from V2 is structural: V3 calls the separately
versioned, condition-blind calibration scorer rather than adding another
result-informed list to a run-local preflight. That scorer rejects contradicted
status, identifier, action, and uncertainty facts as well as accepting the
approved-but-unrevoked source fact.

## Execution and interpretation

The schedule has 12 fresh episodes per delivery-by-dose cell, 72 total. It
pauses operationally after each 24 terminal admissions for 15 minutes, without
looking at treatment results or replacing trials. The completed report will
show all reason-coded outcomes and context-dose cells. It can support only the
held-out Qwen3.8 result; a direct transfer statement needs a separately valid
Qwen3.6 comparator.
