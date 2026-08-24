# Study registry

This index is append-only. A new revision records a new row; it never changes
the status or contents of an executed registration.

| Study version | Status | Registration | Results | Notes |
| --- | --- | --- | --- | --- |
| Design 0001 | design only | N/A | N/A | Program design for the first two studies; no model trials have run. |
| Pilot 0001 | awaiting review | `experiments/current-assist-pilot/registration-v1.md` | N/A | Initial registration state: its registration, four written design reviews, implementation tests, and sealed bundle were complete before any model trial ran. Later execution records appear below. |
| Pilot 0001 execution record | infrastructure failure | `experiments/current-assist-pilot/registration-v1.md` | `results/current-assist-pilot-v1-failure/` | The v1 bundle was admitted after one administrative denial but the worker failed to import before a model request. Retained as evidence; its `model_request_made` flag is known inaccurate. A new registration is required for the corrected runner. |
| Pilot 0002 | awaiting local review | `experiments/current-assist-pilot/amendment-v2.md` | N/A | Same neutral one-episode execution pilot, with absolute worker import path and an immediately-pre-invoke request marker. |
| Pilot 0007 execution record | oracle mismatch | `experiments/current-assist-pilot/amendment-v5.md` | `results/current-assist-pilot-v7-capsule/` | The current Assist model made a request and completed the read-and-edit fixture. The v7 outcome remains `artifact_failure` because its pre-registered oracle accepted only `write_file`, while the normal Deep Agents run used `edit_file`. |
| Pilot 0009 | awaiting execution | `experiments/current-assist-pilot/amendment-v6.md` | N/A | Same one-episode current-Assist pilot, with the pre-registered native `edit_file(file_path)` oracle correction. |
| Pilot 0009 execution record | pass | `experiments/current-assist-pilot/amendment-v6.md` | `results/current-assist-pilot-v9-capsule/` | The admitted current Assist baseline read then edited the target file, produced the exact sealed artifact, and passed. This single episode is baseline evidence only. |
| Pilot 0010 | awaiting execution | `experiments/current-assist-pilot/amendment-v7.md` | N/A | Same one-episode pilot, with success-path model-request accounting bound to the sealed pre-invoke marker. |
