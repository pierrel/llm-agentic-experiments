# Study registration template

Copy this template into `experiments/<study>/registration-v<N>.md` and commit it
before the first real-model trial. Never edit an executed registration. Create
a dated amendment that names the prior registration and the reason for change.

## Identity

- Study and version:
- Registration commit:
- Authors/reviewers:
- Date and model-run start time:

## Comparison axes and settings

- Test fixture/task IDs and exact digests: (the reusable test axis)
- Model ID, revision/weights digest, and configuration digest:
- Harness architecture ID, revision, and configuration digest:
- One generic JSON settings object: (include reasoning controls, decoding,
  provider payload, graph/middleware configuration, limits, and every other
  behavior-affecting setting; secrets must be redacted or referenced by a
  non-secret identifier)
- Cross-run comparison rule: (name which one axis changes and prove the other
  two remain identical; do not combine distinct bundles into one cohort)

## Question and hypothesis

- Natural-language question:
- Confirmatory hypothesis:
- Exploratory questions, if any:

## Minimum adequate setup review

- Registered causal question and the smallest setup capable of answering it:
- Component ledger: for each model, harness feature, setting, task, replicate,
  metric, and external dependency, state the necessity or why it is held fixed:
- Rejected additions and why they would add a confound, cost, or researcher
  discretion without improving the inference:
- Required controls, sample size/power, safety containment, and fidelity
  features that cannot be removed:
- Reviewer and resolution:

## Experimental units and conditions

- Unit of randomization and analysis: (normally one fresh agent run; explain
  any other unit)
- Conditions and their only intended differences: (what exact text differs and
  what stays byte-identical?)
- Exact condition-manifest hashes:
- Declared invariant prompt blocks, tools, schemas, fixtures, and decoding:
- Development tasks and locked confirmation tasks:

## Outcomes and scoring

- Primary outcome and deterministic oracle: (one automatic fixed pass/fail
  checker; an *oracle* is that checker)
- Secondary outcomes:
- Qualitative rubric, reviewer blinding, and adjudication, if used:
- What counts as a timeout, refusal, invalid trace, or infrastructure failure:

## Sampling and inference

- Blocking/pairing variables and randomization seed:
- Position-balance plan: (complete condition cycles, or the fixed adjustment
  used for any remainder)
- Pilot sample and what it may estimate:
- Confirmation sample calculation, minimum worthwhile difference in success
  probability, and target power: (power is the planned chance of detecting that
  worthwhile difference if it is real)
- Planned model/test, confidence interval, multiplicity correction, and
  sensitivity analyses:
- Stopping rule and handling of GPU pauses:

## Reproducibility and integrity

- Model binary/version/weights digest, server configuration, decoding payload,
  and cache policy:
- Harness and fixture commit/digests:
- Prompt/schema equality check:
- Raw-record retention and redaction policy:
- Design-review findings and resolutions:

## Plain-language interpretation

- Predicted result in ordinary language:
- What a result in the predicted direction would mean:
- What a null, mixed, or infeasible result would mean:
- What this study must **not** be used to conclude:
