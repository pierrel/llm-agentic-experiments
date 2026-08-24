# Pre-admission events

This append-only record preserves v3 operational facts. It contains no model
observation and does not alter v3's sealed task, condition, or outcome rules.

## 2026-08-24: first C0 launch failed before a model request

The first scheduled C0 `library-shift` worker was admitted by the shared GPU
wrapper and reached `task-validated`, but it did not reach `model-verified` or
the exact provider-request marker. Its outcome is `infrastructure_invalid` with
`model_request_made: false`; no agent response, tool call, or provider request
was produced. The scheduled trial is terminal and must not be replayed inside
v3.

The retained private raw directory is `results/raw/durable-routing-v3.a08Gg2`
(mode 0700). Its sealed bundle digest is
`4fdb9c23fff72a3ab19aaf5611995cc1d8f8f96fb25894fe7ad6253b06ec7d2f`.

A fail-stop diagnostic under the exact shared-admission environment completed
the same descriptor and model verification and stopped before graph execution.
That verifies the model configuration itself; the cohort failure remains an
unexplained process-path defect. V4 changes only traceback evidence retention
to keep the exception tail, then starts a new cohort rather than rewriting v3.
