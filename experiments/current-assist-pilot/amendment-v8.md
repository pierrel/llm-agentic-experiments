# Current Assist pilot v8 amendment

Pilot v7's worker-result recovery finalized malformed JSON, types, and paths,
but a malformed trace message such as a JSON list reached the oracle and raised
`AttributeError`. That could leave an admitted episode without its required
reason-coded outcome and final seal.

Pilot v8 treats that malformed trace as a marker-backed `provider_error`, just
like every other malformed worker result. A deterministic regression test
writes the pre-invoke marker and a non-message trace element, then requires a
finalized provider error. The fixture, model, reasoning setting, harness
profile, native edit oracle, neutral condition, one-episode schedule, and
no-replay policy are unchanged. This is a new registration and requires a new
execution record; v10 remains unchanged.
