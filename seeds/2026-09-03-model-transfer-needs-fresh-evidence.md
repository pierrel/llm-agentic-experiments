# A model upgrade can change a guidance-treatment response surface

- **Origin:** Pierre's 2026-09-03 observation that the earlier
  retrieved-versus-handed guidance work ran on Qwen3.6 while current Assist now
  serves Qwen3.8-27B-UD-Q4_K_XL.
- **Intervention:** Hold the task, fixture, oracle, harness architecture,
  reasoning setting, decoding, rendered guidance conditions, and schedule form
  fixed, while registering the current Qwen3.8 model identity and weights as a
  new model condition.
- **Prediction:** The size, direction, or context-dose location of any
  retrieved-versus-handed guidance difference may change under Qwen3.8. A
  Qwen3.6 result therefore cannot stand in for current Assist.
- **Boundary:** A model transfer does not repair an invalid task oracle, and
  results from different model identities must remain separate sealed bundles,
  not pooled as one cohort. It also does not establish transfer to another
  harness, reasoning setting, skill catalog, or task family.
- **Possible experiment:** First pass a standalone, condition-blind oracle
  calibration gate for the held-out handoff task. Then run a newly registered,
  fully sealed Qwen3.8 confirmation cohort and compare its reported outcome
  surface descriptively with the earlier Qwen3.6 history without combining
  records.
