# V5 execution finding: the evidence is sealed, but the cohort is not interpretable

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

All 72 scheduled trial identities, their captured provider requests, traces, and
terminal records verify against sealed bundle
`9fcb081c79f9fa606ffdc2eb321aa7a493970a51b9a86c00a7ce07a1a26734c8`.
That proves artifact integrity, not execution-protocol compliance.

The sealed registration required a 900-second pause before resuming an
incomplete bounded batch. The trace for terminal trial 53 was written at
2026-09-11T04:47:35Z and trial 54 at 2026-09-11T04:49:53Z: a 138-second gap.
An older scheduled runner had been waiting on the output lock. When it acquired
the lock at 53 completed outcomes, the sealed runner only checked cooldowns at
counts divisible by 24, so it bypassed the current `batch-cooldown.json` record.

This run is therefore an invalid protocol run. Do not use `report.json` to
support or reject the retrieved-versus-always-present guidance hypothesis.

## Limits

The artifact oracle, current Qwen 3.8 model, reasoning-disabled setting, and
Deep Agents harness were all captured and verified, but the prescribed execution
break was not honored. No effect estimate, cell comparison, or product inference
from this cohort is durable evidence. The result also does not establish transfer
across tasks, models, harnesses, or reasoning settings.

## Handoffs

The durable process learning is narrow: an output lock serializes writes, but a
resume policy must validate the persisted batch boundary after acquiring that
lock. A fresh preregistered study revision must repair that rule, add a
lock-wait regression test, and rerun the held-out cohort. This is laboratory
infrastructure evidence, not a blog seed or an Assist product proposal.
