# Durable actions should not be claimed before their capability is used

- **Origin:** Assist production thread `20260723170746-d10af2fb` and Pierre's
  2026-08-21 review. A request to remove a recurring meditation reminder was
  answered as completed without loading the scheduling capability or changing
  the schedule. The same turn also turned a conditional future preference into
  a private-memory note without establishing a durable action for it.
- **Intervention:** compare general capability-selection and completion-evidence
  guidance with the current skill catalog guidance. The proposed guidance would
  require a matching capability before an agent represents a stateful outcome
  as complete, while preserving direct answers for genuinely response-only
  requests.
- **Prediction:** on natural stateful requests, the agent more often loads the
  relevant skill, performs its state-changing operation, and reports only the
  resulting state. Unsupported success claims fall.
- **Boundary:** a response-only request, a deterministic direct operation, and
  a request whose capability is intentionally unavailable must not cause
  unnecessary skill loads or a fabricated completion claim.
- **Possible experiment:** use synthetic, non-production fixtures for paired
  create/change/remove/conditional-follow-up requests across scheduling and
  thread state. Record skill selection, operation trace, persisted fixture
  state, and whether the final response is supported by that trace. Compare
  catalog-description-only, general evidence guidance, and their combination
  under a preregistered split.
