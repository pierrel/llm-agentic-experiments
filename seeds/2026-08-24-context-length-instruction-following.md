# Instruction following may degrade as rendered context length increases

- **Origin:** Pierre's 2026-08-24 request for a first-class experimental
  treatment of where hypotheses hold, including quantifiable context length,
  task complexity/length, and skill-catalog size.
- **Intervention:** Hold the model, harness architecture, task, natural user
  request, instruction wording, tool schemas, decoding, and fixture fixed while
  varying only a sealed, semantically non-conflicting context payload to achieve
  preregistered rendered-input token targets. Measure the actual rendered token
  count, not only the configured padding length.
- **Prediction:** Instruction-following and deterministic artifact success may
  stay flat at low context lengths, then decline past a model- and task-specific
  range. The curve may also be flat or non-monotonic; a single short-versus-long
  comparison cannot establish its shape or threshold.
- **Boundary:** The added context must not contain competing instructions,
  relevant task facts, secret data, or hidden answer cues. This study estimates
  only the pinned model, harness, reasoning setting, instruction, and task; it
  does not establish that task complexity, skill count, or another architecture
  has the same response curve.
- **Possible experiment:** Register a context-length dose-response study with a
  small preregistered grid spanning the usable rendered-context range, fresh
  episodes at every point, and a deterministic procedure-plus-artifact oracle.
  Its first goal is to detect whether a degradation exists; its second is to
  estimate the performance curve and any practically meaningful threshold with
  uncertainty. Preserve the exact rendered request and token count for every
  episode, then add complexity and skill-count axes only in separately powered
  extensions.
