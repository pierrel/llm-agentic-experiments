# Study registration template

Copy this template into `experiments/<study>/registration-v<N>.md` and commit it
before the first real-model trial. Never edit an executed registration. Create
a dated amendment that names the prior registration and the reason for change.

## Identity

- Study and version:
- Registration commit:
- Authors/reviewers:
- Date and model-run start time:

## Question and hypothesis

- Natural-language question:
- Confirmatory hypothesis:
- Exploratory questions, if any:

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
