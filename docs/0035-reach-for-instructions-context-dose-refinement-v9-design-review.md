# Reach-for-instructions context-dose refinement V9 design review

## Minimum adequate setup

V8 completed all 72 episodes and found G02 11/12 versus G01 5/12 at 3,600
inert lines, while low context favored G01. The next question is therefore not
whether retrieval wins generally. It is whether the apparent high-context
region is stable and where its shape changes. V9 retains V8's one fixture,
model, current reasoning profile, Deep Agents loop, loader schema, procedure,
oracle, and 12 episodes per cell. It replaces only the sealed context grid and
fresh schedule.

The grid is 1,800, 2,700, 3,600, and 4,500 inert lines. Repeating 3,600 tests
the observed cell without pooling V8. The adjacent lower and higher doses
bracket it. Four doses are the smallest useful map of a local response region;
adding a low-context control merely repeats V8's already observed reversal and
would spend episodes without locating the high-context boundary.

## Review findings

- **Scientific integrity:** V9 receives a new study ID, seed, bundle, tag, and
  96 fresh episodes. V8 remains sealed and is never pooled into a V9 outcome.
  The V8 task is intentionally retained because task transfer is a later,
  separate question.
- **Statistical rigor:** The experimental unit is one fresh episode. Twelve
  episodes per cell matches V8 and permits descriptive cell comparison, not a
  fitted threshold or a claim of statistical significance. The analysis reports
  all terminal outcomes, including model and tool failures. There is no
  result-dependent stopping or dose selection after admission.
- **Agentic harness fit:** Both arms retain the same Deep Agents tools,
  filesystem fixture, loader schema, model request capture, and deterministic
  condition-blind handoff oracle. The runner seals every inherited V8 input,
  the new context mapping, the V9 registration, and the pre-rendered request
  digest for each scheduled trial.
- **Minimum setup:** A new fixture, catalog-size axis, architecture comparison,
  LLM judge, production thread, or extra delivery treatment would confound the
  local context question. They are excluded. A fresh task family follows only
  if this within-task curve is interpretable.
- **Pre-admission integrity r2:** Copilot caught an inherited Qwen3.6 bundle
  identity and tests that did not compare the sealed schedule or tag to V9's
  declarations. The runner now writes the current Qwen3.8 identity and the
  no-model contract binds the exact 96-trial schedule, r2 tag, and model
  revision. No V9 model request occurred before the correction.
- **Pre-admission integrity r3:** Admission now recomputes and compares V9's
  exact seed, schedule, registration tag, current model identity, and complete
  current-profile settings instead of accepting a merely self-consistent
  bundle. The V9 contract also invokes the inherited V8 calibration gate. The
  public worker command remains a cooperative scheduler implementation detail,
  not a model-provider authorization boundary; hardening local provider access
  is separate infrastructure work. No V9 model request occurred before r3.
- **Pre-admission integrity r4:** Admission now also pins the Deep Agents
  architecture identity and fixed tool schema. The no-model suite independently
  perturbs the randomization seed and rejects self-consistent schedule, seed,
  tag, model, fixture, architecture, and tool-schema rewrites. Each worker
  still verifies its actual provider-bound request against the sealed digest;
  re-rendering every request at parent admission would require the worker's
  isolated runtime configuration. No V9 model request occurred before r4.

## Decision

V9 is eligible for implementation and no-model integrity checks. It requires a
committed registration, sealed tag, and full local/Copilot review before its
first model request.
