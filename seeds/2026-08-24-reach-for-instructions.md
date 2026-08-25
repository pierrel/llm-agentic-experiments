# Retrieved procedural guidance may beat always-present guidance under context pressure

- **Origin:** Pierre's 2026-08-24 observation from roughly a month of Assist
  design: an agent may follow a procedure better when it recognizes the task
  shape and loads the relevant skill than when the full procedure is always in
  its system prompt.
- **Intervention:** Compare two otherwise identical Assist configurations. In
  the control, the full procedure is permanently present in the system prompt.
  In the treatment, the system prompt contains only the same skill discovery
  surface and a shape-matched skill description; the agent loads the skill body
  containing the same procedure before performing the task. Hold model, tool
  schemas, fixture, decoding, harness, and procedural wording fixed after the
  treatment skill is loaded.
- **Prediction:** On procedure-heavy tasks with an obscure shape or a large
  unrelated system context, the treatment will more often complete the
  deterministic primary outcome and follow the required procedure. On simple
  tasks with a small system prompt, there may be little difference or the extra
  retrieval step may make the treatment worse.
- **Boundary:** A gain must not be credited merely to different instruction
  wording, extra tools, changed context length, or a leading user prompt. The
  treatment must load the skill before relying on its procedure; failure to load
  it is an outcome, not a reason to supply the procedure ad hoc. This does not
  establish transfer to a different model, skill description, reasoning setting,
  or harness architecture.
- **Possible experiment:** Register a matched two-condition study with the same
  natural user tasks and oracle in both arms. Include a deliberately simple
  small-context task as a negative-control stratum, plus procedure-heavy
  large-context and obscure-shape strata. Capture rendered prompts, the skill
  discovery surface, actual skill-load events, tool schemas, and final artifacts
  before scoring procedure compliance and artifact success blind to condition.
