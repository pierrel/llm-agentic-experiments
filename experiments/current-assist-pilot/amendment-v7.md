# Current Assist pilot v7 amendment

Pilot v6 passed its registered episode, but a review found that the successful
worker-result branch set `model_request_made` without consulting the same
sealed pre-invoke marker used by every other terminal branch. The successful
worker itself proves a result was returned, but the experiment's request
accounting contract is evidence-based rather than inferred.

Pilot v7 records success and artifact failure from that marker too. Its
deterministic worker test writes the marker at the declared pre-invoke point.
The fixture, model, reasoning setting, harness profile, native edit oracle,
neutral condition, one-episode schedule, and no-replay policy are unchanged.
This is a new registration and requires a new execution record; v9 remains
unchanged.
