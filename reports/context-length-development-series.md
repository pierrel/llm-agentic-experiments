# Context-length instruction-following development series

## Question and runtime

Does the current Qwen3.6-27B Q4_K_M model, reasoning disabled, preserve a
case-handoff procedure as inert context grows in the current Deep Agents
filesystem/TODO/task loop? All admitted episodes used the clean Assist commit
`93e2af053440931745a1e827b401c86527134be3`, the hashed GGUF, and realized
first-request sizes of 6,124, 31,324, and 106,924 tokens.

## Evidence

| Registered variant | Task/oracle change | Low | Medium | High | Interpretation |
| --- | --- | --- | --- | --- | --- |
| V1 r3 | Minimum four-record handoff, exact facts | pass | pass | pass | No detectable difference in the minimum task. |
| V2 | Nine-record reconciliation handoff, exact facts | pass | phrase failure | phrase failure | Both apparent failures preserved the fact but omitted “one receipt image.” |
| V3 | Same V2 task, predeclared retained-image alternatives | phrase failure | pass | pass | The low failure preserved the fact but used “duplicate image” instead of “duplicate receipt image.” |

The `v1` and `v1-r2` sealed bundles made no model request: they respectively
rejected an unverifiable copied Assist tree and a fixture-path preflight bug.
They are retained as setup history, not behavioral evidence.

## Learning and next step

This series does not support a context-length degradation claim. Its durable
learning is about measurement: exact phrase matching can create false
dose-response patterns when the required fact has several natural forms.

Before a held-out confirmation, build and calibrate a task oracle independently
of the intervention, with predeclared alternate evidence forms or a separately
validated semantic extractor. Do not change Assist guidance from this series.
