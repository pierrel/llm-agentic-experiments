# Recursion budget is a behavioral setting

- **Origin:** `results/current-assist-baseline-v7/learning.md`, where one
  current-Assist historical pilot exhausted its 12-step recursion limit.
- **Intervention:** Change only the sealed recursion-limit setting in fresh,
  otherwise matched current-Assist edit episodes.
- **Prediction:** Completion and the captured tool path will differ by loop
  budget, so the budget belongs in every between-run setting comparison.
- **Boundary:** This does not predict that a larger budget improves unrelated
  tasks or that loop exhaustion is caused by prompt guidance or the model.
- **Possible experiment:** Preregister a small matched cohort with complete
  provider-schema and source-tree sealing, then compare reason-coded outcomes
  and tool-event paths across two recursion limits.
