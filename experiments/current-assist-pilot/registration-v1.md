# Current Assist execution-path pilot, registration v1

Status: design only. No model result exists.

## Identity

- Study and version: Current Assist execution-path pilot v1
- Registration commit: filled only when this registration and its sealed bundle
  are committed together
- Unit: one fresh model-and-agent episode
- Scope: establish the real execution/evidence path, not a behavioral effect

## Exact comparison identity

- Test: `fixtures/current-assist-read-before-edit.json`, its natural request
  “Please change the budget in my note to $25.”, and its deterministic
  read-before-edit oracle.
- Model: `Qwen_Qwen3.6-27B-Q4_K_M.gguf`; the trial refuses admission until a
  non-secret operator-recorded model-weights SHA-256 is in the bundle.
- Harness: Assist's `select_assistant_model` plus Deep Agents
  `create_deep_agent` over Deep Agents 0.6.1, LangChain 1.3.1, and LangGraph
  1.2. The adapter pins reasoning off.
- Settings: generic JSON must record provider base-URL shape without a secret,
  model ID, weights digest, `{ "enabled": false }` reasoning setting,
  decoding, context limit, Assist source commit, package versions, graph
  profile, tool/middleware/subagent set, timeout, recursion/turn limit, and
  no-client-replay policy.

The test's virtual file/skill fixture is materialized into a private temporary
directory for one episode. The adapter mounts it through Deep Agents' normal
virtual filesystem backend. It supplies only Deep Agents' filesystem/TODO tools
and task tool, with no network-capable navigation/travel tools or subagents.
That confinement is a declared fidelity limitation, not an unrecorded
substitution for production.

## Outcome and sampling

The one registered episode is a pilot smoke. Its primary outcome is the
existing deterministic artifact predicate: `budget-note.txt` must be exactly
`Budget: $25.\n` and the run must show an inspection before the edit. It is
neither powered nor confirmatory. The complete denominator is one scheduled
episode. A resource refusal is administrative and retries that same episode;
post-request timeout, provider error, invalid tool call, loop exhaustion, and
artifact failure are retained reason-coded outcomes with no automatic replay.
After a resource refusal, schedule one ten-minute retry. Stop retrying after
sixty minutes of continued production reservation and report that external
capacity condition rather than treating it as an experiment outcome.

## Design reviews and resolutions

| Lens | Finding | Resolution |
| --- | --- | --- |
| Scientific integrity | A smoke result could be mistaken for support for an Assist behavior or a prompt. | Register one operational question, neutral single condition, explicit no-behavioral-learning limit, sealed bundle/tag, raw-trace hashes, and no product handoff. |
| Statistical rigor | One episode has no inferential power and retries can bias a denominator. | Label it pilot only; one fixed scheduled unit; record every post-request terminal outcome; retry only pre-request resource denials on the same unit. |
| Agentic harness fit | A raw chat loop would not be Assist; unrestricted production tools would violate hermeticity. | Use Assist's `select_assistant_model` and Deep Agents `create_deep_agent`; pin packages/source/profile; use a fresh private virtual backend; omit navigation/travel/subagents; and rely on the non-executable backend to make `execute` fail closed. |
| Minimum adequate setup | Full web-thread, sandbox, subagent, and network stacks add cost and confounds without testing the execution path. | Retain only the production model selector, Deep Agents tool-loop/backend contract, fixture, oracle, trace, timeout, and admission control. Omit web state, user data, network, subagents, alternate model/architecture, and a task bank. |

No unresolved design finding permits a model request. The implementation must
add deterministic tests for Git binding, required weights digest, denied
admission accounting, one-worker command construction, direct-mode rejection,
and post-request outcome retention before a trial is admitted.
