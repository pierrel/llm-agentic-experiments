# Held-out confirmation V2: invalid before completion

V2 stopped after its first predeclared 24-terminal-episode batch. The sealed
bundle was `c804722dd67ed61779e4eb5f7b6191dbe10d3908947bcf5674d5fe161296749e`.
It ran through the pinned current Assist model and Deep Agents harness, after
three retained pre-admission attempts on the same first trial: two shared-lock
denials and one scheduler attempt without a Codex thread identity. None made a
model request or advanced the schedule.

The 24 admitted terminal outcomes contain 9 passes, 3 source-before-inventory
failures, 1 multiple-JSON-output failure, and 11 `unsupported or incomplete
fact` failures. A condition-blind artifact audit found that 10 of those 11
handoffs state the grounded fact in forms V2's preflight did not admit, such as
`removal approved but not yet executed`, `approved_not_revoked`, or
`approved_for_removal_not_revoked`. The remaining one says only `active` and is
an actual incomplete-status failure. V2's calibrated oracle is therefore still
too narrow; its outcome counts must not be interpreted as evidence about
guidance delivery, including at the completed batch boundary.

The private raw admission and outcome-chain file hashes are respectively
`32002a2b3512bf503b4be19dddf1d16d28e066096a69447535daa00da9ad3b44` and
`bde939f9e6922c89af601ae8b099939dac8ad4ba792684e501f2ea4908c4edaf`.
The run is not a finalized result capsule.

## Blocking finding and recommendation

This is the second fresh oracle calibration failure on the held-out task. A
third version could pre-register a broader, explicitly tested status grammar
and begin with a stronger condition-blind adversarial corpus. But another
result-informed rerun risks repeating the same pattern. The recommended next
step is to pause the delivery comparison and design a standalone oracle
calibration gate for this task family: enumerate accepted and rejected status,
owner, identifier, and action forms before any new confirmation cohort. Only a
passing gate should authorize a fresh V3 confirmation.

The alternative is to replace this structured-handoff task with a task whose
primary outcome has a less semantically open-ended deterministic oracle. That
would reduce oracle risk but changes the held-out task family, so it would test
a different transfer surface.
