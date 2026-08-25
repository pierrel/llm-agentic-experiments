# Reach-for-instructions development registration v2

V1 was sealed but never admitted to a model. An admission-gated runtime probe
found that its worker wrapper would pass `PYTHONPATH=...` as an executable
argument rather than an environment assignment. V2 changes only that wrapper:
it sources the existing private deployment environment, exports the declared
`PYTHONPATH`, then executes the same Python worker. The V1 bundle and tag remain
as an unexecuted setup record.

## Question and conditions

For the pinned current Assist Deep Agents loop and model, does a reimbursement
handoff procedure work better when the agent retrieves it through a
shape-matched skill than when the host presents the same procedure in system
context before the first decision?

Both arms expose the same `load_skill(name)` tool and catalog entry. The handed
arm contains the full procedure before the first decision; the reached arm has
only the catalog until it loads the same procedure. Model, filesystem backend,
tool schemas, fixture, user request, decoding, recursion limit, and skill body
are fixed.

## Development response surface and outcomes

`C-low`, `C-medium`, and `C-high` use 0, 900, and 3600 inert declarative filler
lines. They are crossed with opaque delivery IDs `G01` and `G02`; three fresh
episodes per cell form an 18-episode, deterministically interleaved development
screen. The local provider offers no sealed generation-seed control, so trial
seeds identify schedule entries rather than matched samples. Actual first
provider-input token counts are retained.

Primary success requires one JSON handoff with the declared grounded fields,
unchanged source records, and an inventory plus every source read before the
handoff write. The secondary process outcome is skill loading before the first
source read. The deterministic oracle sees no condition ID and accepts direct
structured representations rather than one literal prose phrase. Every admitted
terminal outcome remains reason-coded; a shared-admission denial retries the
same sealed trial before the schedule advances.

This is exploratory development evidence only. It cannot establish a general
effect or transfer across tasks, models, reasoning settings, architectures,
complexities, or catalog sizes.
