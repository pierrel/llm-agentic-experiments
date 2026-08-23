# Study registry

This index is append-only. A new revision records a new row; it never changes
the status or contents of an executed registration.

| Study version | Status | Registration | Results | Notes |
| --- | --- | --- | --- | --- |
| Design 0001 | design only | N/A | N/A | Program design for the first two studies; no model trials have run. |
| Pilot 0001 | awaiting review | `experiments/current-assist-pilot/registration-v1.md` | N/A | One current-Assist execution-path pilot. Registration, four written design reviews, implementation tests, and a sealed bundle are complete; no model trial has run. |
| Pilot 0001 execution record | infrastructure failure | `experiments/current-assist-pilot/registration-v1.md` | `results/current-assist-pilot-v1-failure/` | The v1 bundle was admitted after one administrative denial but the worker failed to import before a model request. Retained as evidence; its `model_request_made` flag is known inaccurate. A new registration is required for the corrected runner. |
| Pilot 0002 | awaiting local review | `experiments/current-assist-pilot/amendment-v2.md` | N/A | Same neutral one-episode execution pilot, with absolute worker import path and an immediately-pre-invoke request marker. |
