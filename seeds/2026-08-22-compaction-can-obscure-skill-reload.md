# Compaction can obscure the need to reload a skill

- **Origin:** Pierre's 2026-08-22 review of Assist production thread
  `20260723170746-d10af2fb`. That thread's schedule-action miss preceded any
  compaction, but inspection of other production checkpoints showed that a
  compacted summary can retain that a skill was used without retaining its full
  instructions. Assist hides the tools supplied by that skill again at the
  start of every new invocation.
- **Intervention:** compare an ordinary multi-turn continuation with the same
  continuation after framework compaction, holding the natural user request,
  persisted application state, available skill catalog, and model settings
  constant. A later study can compare general reload guidance if compaction
  alone causes a measurable loss.
- **Prediction:** when the summary records prior skill use but omits the skill
  instructions, the agent reloads the matching skill and completes the
  stateful action less often than in the uncompacted continuation.
- **Boundary:** summaries that retain the actual operating instructions,
  capabilities whose tools are always visible, and response-only follow-ups
  should not exhibit this effect. The cited production miss is not evidence for
  the prediction because that thread had not compacted.
- **Possible experiment:** use synthetic schedule fixtures and paired trial
  histories. In both conditions, establish the same reminders and prior skill
  use; in treatment, replace the old portion with the exact Deep Agents summary
  wrapper containing a neutral record of that use but no full skill
  instructions. Ask
  naturally to remove the nightly reminder. Record first tool selection, skill
  reload, list/delete trace, persisted target/control state, and evidence-backed
  final response. Verify rendered requests differ only in the declared history
  representation before admitting trials.
