# Current Assist read-before-mutate baseline

- **Origin:** Pierre's request to create a minimum current-Assist experimental
  baseline before later model, harness, architecture, or settings transfers.
- **Intervention:** Run the unmodified current Assist Deep Agents/ReAct-style
  harness with its current local model and default reasoning setting on an
  isolated note-edit request.
- **Prediction:** The agent preserves the initial note text,
  adds the requested line once, and its trace shows it read the note before
  changing it.
- **Boundary:** A correct final artifact without a preceding read
  is still a successful artifact outcome but contradicts the trace expectation;
  a failure does not establish that the architecture or model is generally
  incapable.
- **Possible experiment:** Run the isolated note-edit task with the sealed
  read-before-mutate oracle, then compare only a newly registered model,
  harness, architecture, or setting condition against this baseline.
