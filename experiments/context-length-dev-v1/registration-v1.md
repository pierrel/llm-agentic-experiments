# Context-length instruction-following development registration v1

## Question

Does the current Qwen3.6-27B Q4_K_M model, in the current Deep Agents
ReAct-style filesystem loop, preserve a case-handoff procedure as unrelated
context grows? This is a development screen, not a confirmation claim.

## Fixed setup

- Task: `fixtures/context-length-case-handoff.json`, a fresh synthetic
  workspace with one convention and three source records.
- User request: “Please prepare the handoff for the Oakridge reimbursement
  case. The workspace has the material.”
- Model and settings: the running local Qwen3.6-27B Q4_K_M GGUF,
  SHA-256 `d797b531c527bea28a04fdb326515c43114f798a4fa2a5c1c0e0cffaeaa6fd09`,
  reasoning disabled, temperature 0.1, maximum output 1200, and one 20-step
  Deep Agents filesystem/TODO loop.
- Oracle: one correctly located four-section handoff, unchanged sources, all
  required case facts including the duplicate-receipt uncertainty, plus an
  inventory and all reads before the first write.

## Factor, schedule, and analysis

The sole varying factor is sealed inert declarative filler before the unchanged
system procedure. `C-low`, `C-medium`, and `C-high` contain respectively 0,
900, and 3600 generated lines. The three fresh episodes run in a deterministic
pseudorandom order from seed `20260825`. The provider-reported first-request
`input_tokens` is the realized dose.

Every admitted episode remains in the denominator as pass, artifact failure,
timeout, or provider error. A GPU admission denial is recorded and the same
trial is retried later. The result reports condition, reason-coded outcome,
and realized prompt tokens. It does not estimate a general dose-response curve
or justify an Assist change.

## Development policy

If this sweep shows no detectable outcome difference, create two more sealed,
fully reviewed development versions where feasible. Each may vary only an axis
declared in its registration. Confirmation tasks remain held out.
