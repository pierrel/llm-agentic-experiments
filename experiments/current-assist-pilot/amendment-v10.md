# Current Assist pilot v10 amendment

The worker previously let a non-object JSON descriptor trigger Python's
incidental `TypeError` while calculating its keys. Pilot v10 rejects that
descriptor explicitly as an invalid descriptor before any task construction.
It also removes an unused coordinator import.

The fixture, model, reasoning setting, harness profile, native edit oracle,
neutral condition, one-episode schedule, and no-replay policy are unchanged.
This is a new registration and requires a new execution record; v11 remains
unchanged.
