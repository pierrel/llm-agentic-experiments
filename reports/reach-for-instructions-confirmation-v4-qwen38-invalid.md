# Qwen3.8 confirmation V4: invalid before completion

V4 admitted 22 terminal Qwen3.8 episodes and then stopped before the next
admission. Its schedule was generated with fresh seed `20260904`, but the
sealed bundle's `registration.randomization_seed` retained the V2 constant
`20260827`. The registration therefore does not faithfully describe the
executed schedule.

This is a configuration-recording defect, not a treatment outcome. The local
raw admission and outcome chains are retained for audit, but none of the 22
episodes is scored, pooled, or used to update a learning. Completing the
remaining schedule would not repair the mismatch.

The smallest corrective path is a fresh V5 registration that binds the seed in
both schedule generation and the sealed registration, then renders and checks
its provider requests before its first admission. That is a new cohort; it
must not reuse V4 outcomes. Whether to make that correction is left for the
high-touch first-experiment decision.
