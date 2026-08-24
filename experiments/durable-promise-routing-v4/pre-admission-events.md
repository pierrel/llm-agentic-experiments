# Pre-admission events

This append-only record preserves v4 operational facts. It contains no model
observation and does not alter v4's sealed task, condition, or outcome rules.

## 2026-08-24: first C0 launch failed before a model request

The first scheduled C0 `library-shift` worker was admitted by the shared GPU
wrapper and reached `task-validated`, but it did not reach `model-verified` or
the provider-request marker. Its outcome is `infrastructure_invalid` with
`model_request_made: false`; no agent response, tool call, or provider request
was produced. The retained private raw directory is
`results/raw/durable-routing-v4.ItmcO8` (mode 0700).

V4 retained the traceback tail and identified the cause: the coordinator used
`Path.resolve()` on the virtualenv `python` path. That follows the virtualenv
symlink to the system interpreter, which lacks `httpx`; importing
`assist.model_manager` therefore failed before model verification. This is a
runner defect, not an Assist or model behavior. V5 preserves the executable
path, adds a regression test, and begins a new cohort rather than altering or
replaying v4.
