# Pre-admission events

This append-only record preserves v2 operational facts. It contains no model
observation and does not alter v2's sealed task, condition, or outcome rules.

## 2026-08-24: first C0 launch failed before a model request

The first scheduled C0 `library-shift` worker entered through the shared GPU
admission wrapper, then exited before its first provider request. Its lifecycle
record remained `launch-intent`; the private outcome chain records
`infrastructure_invalid` with `model_request_made: false`. No agent response,
tool call, or provider request was produced. The scheduled trial is terminal
and must not be replayed inside v2.

The retained private raw directory is `results/raw/durable-routing-v2.VqcNED`
(mode 0700). Its bundle digest is
`41781f954b37c4b810e88860572ce3b08ec71155cba9b462f12f74896521bb97`.
The `registration-v2.md` prose names an earlier clerical digest; the sealed
`bundle.json` and this event record are authoritative for what was admitted.

The exact model-identity preflight and a fail-stop invocation through the same
admission wrapper both passed separately. That narrows the failure to an
unobserved worker-setup boundary, not the prompt, the task, or the served model.
A successor adds checkpoint-only lifecycle evidence before a new cohort is
registered; it does not modify or rerun this one.
