# Current Assist read-before-mutate baseline

- **Intervention:** Run the unmodified current Assist Deep Agents/ReAct-style
  harness with its current local model and default reasoning setting on an
  isolated note-edit request.
- **Predicted observable outcome:** The agent preserves the initial note text,
  adds the requested line once, and its trace shows it read the note before
  changing it.
- **Boundary/counterexample:** A correct final artifact without a preceding read
  is still a successful artifact outcome but contradicts the trace expectation;
  a failure does not establish that the architecture or model is generally
  incapable.
- **Origin:** Pierre's request to create a minimum current-Assist experimental
  baseline before later model, harness, architecture, or settings transfers.
