# Study registry

This index is append-only. A new revision records a new row; it never changes
the status or contents of an executed registration.

| Study version | Status | Registration | Results | Notes |
| --- | --- | --- | --- | --- |
| Design 0001 | design only | N/A | N/A | Program design for the first two studies; no model trials have run. |
| current-assist-baseline-v1 | superseded before model | `experiments/current-assist-baseline-v1/bundle.json` | Unsealed pre-request admission record | Worker import failed before a model request. |
| current-assist-baseline-v2 | superseded before model | `experiments/current-assist-baseline-v2/bundle.json` | Unsealed admission denial | Shared LLM resource was busy; no model request. |
| current-assist-baseline-v3 | superseded before model | `experiments/current-assist-baseline-v3/bundle.json` | None | Retry-accounting correction registered; no admission attempted. |
| current-assist-baseline-v4 | superseded before model | `experiments/current-assist-baseline-v4/bundle.json` | None | Request-capture design corrected before model use. |
| current-assist-baseline-v5 | reported infrastructure failure | `experiments/current-assist-baseline-v5/bundle.json` | Sealed outcome and admission logs | Assist template assets were unavailable before a model request. |
| current-assist-baseline-v6 | reported infrastructure failure | `experiments/current-assist-baseline-v6/bundle.json` | Sealed outcome and admission logs | Assist checkpointer identity was missing before a model request. |
| current-assist-baseline-v7 | reported | `experiments/current-assist-baseline-v7/bundle.json` | Sealed outcome and admission logs | One real current-Assist episode hit its recursion limit after one captured provider request. |
