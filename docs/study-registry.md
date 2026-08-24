# Study registry

This index is append-only. A new revision records a new row; it never changes
the status or contents of an executed registration.

| Study version | Status | Registration | Results | Notes |
| --- | --- | --- | --- | --- |
| Design 0001 | design only | N/A | N/A | Program design for the first two studies; no model trials have run. |
| Durable-promise orchestration v1 | exploratory, unsealed | `experiments/durable-promise-orchestration-v1/registration.md` | `results/2026-08-24-durable-promise-orchestration-v1/report.md` | Assist-side directional prompt exploration. It does not satisfy the sealed-harness contract and must not be treated as a confirmation study. |
| Durable-promise capability routing v1 | invalid preflight, no model request | `experiments/durable-promise-routing-v1/registration-v1.md` | `experiments/durable-promise-routing-v1/pre-admission-events.md` | The first admitted worker failed before any provider request. Its private chain and trace are retained; it is not baseline evidence. |
| Durable-promise capability routing v2 | invalid preflight, no model request | `experiments/durable-promise-routing-v2/registration-v2.md` | `experiments/durable-promise-routing-v2/pre-admission-events.md` | Its first C0 worker failed before a provider request. The sealed private evidence is retained and is not baseline evidence. |
| Durable-promise capability routing v3 | invalid preflight, no model request | `experiments/durable-promise-routing-v3/registration-v3.md` | `experiments/durable-promise-routing-v3/pre-admission-events.md` | Its first C0 worker reached task validation but failed before model verification or a provider request. The sealed private evidence is retained and is not baseline evidence. |
| Durable-promise capability routing v4 | registered pilot, pre-admission | `experiments/durable-promise-routing-v4/registration-v4.md` | N/A | Clean successor to v3 with traceback-tail evidence retention. The 24 rows are a pilot only; a fresh task bank is required for confirmation. |
