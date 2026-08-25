# Context-length instruction-following development registration v1, fixture-path revision

This supersedes the unrun `context-length-dev-v1-r2` bundle. Its preflight
rejected every fixture path before model invocation because the worker checked
the resolved path instead of the fixture-relative input. The earlier bundle is
preserved and no behavioral result was produced.

The question, fixture contents, natural user request, conditions, decoding,
model weights, runtime-source enforcement, reasoning setting, schedule seed,
and deterministic oracle are unchanged. The sole implementation change is a
tested fixture-relative path check that rejects absolute and parent-traversal
paths before writing the isolated workspace.

The three fresh episodes run in deterministic pseudorandom order from seed
`20260825`. This remains a three-episode development screen. If it shows no
detectable difference, the next two development registrations must be fully
reviewed and sealed before their model runs.
