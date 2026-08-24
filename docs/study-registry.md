# Study registry

This index is append-only. A new revision records a new row; it never changes
the status or contents of an executed registration.

| Study version | Status | Registration | Results | Notes |
| --- | --- | --- | --- | --- |
| Design 0001 | design only | N/A | N/A | Program design for the first two studies; no model trials have run. |
| Durable-promise orchestration v1 | exploratory, unsealed | `experiments/durable-promise-orchestration-v1/registration.md` | `results/2026-08-24-durable-promise-orchestration-v1/report.md` | Assist-side directional prompt exploration. It does not satisfy the sealed-harness contract and must not be treated as a confirmation study. |
| Durable-promise capability routing v1 | design, sealed adapter pending | `experiments/durable-promise-routing-v1/registration-v1.md` | N/A | New two-condition routing study. Old durable-promise rows are development diagnostics; new confirmation rows and the adapter must be sealed before model admission. |
