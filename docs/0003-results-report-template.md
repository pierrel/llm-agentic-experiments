# Results report template

Each completed cohort receives a new append-only report. A report presents all
scheduled trials, not only successful or interpretable ones.

## Plain-language answer

Start with the direct answer. For example: “In this locked task cohort, local
repeat succeeded X/Y times and system-only A/B; the estimated difference was D
percentage points, with an interval of … . This does/does not support the
preregistered hypothesis for this model and task bank.” State what a reader
should not generalize from the result.

## Provenance

- Registration version and commit:
- Harness, fixture, and analysis commits:
- Model/configuration digests:
- Trial-record manifest hash and raw-record retention location:
- Any approved registration amendments:

## Execution accounting

| Condition | Scheduled | Admitted | Completed | Timeout/refusal | Infrastructure-invalid | Scored |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |

Explain every missing or repeated trial without looking at treatment outcomes.
“Admitted” means the shared GPU scheduler allowed a model request. A model
timeout, refusal, loop-budget failure, or invalid tool call remains in the
primary denominator as a scored artifact failure with its reason code.
“Infrastructure-invalid” is reserved for a logged fault before any model
request; only that case may receive the one preregistered replacement attempt.

## Primary outcome

State the preregistered effect estimate, interval, paired/block-aware analysis
(compare like task/replicate blocks rather than pooling unlike runs), and
decision rule. Report task-level values as well as the pooled estimate.

## Secondary and exploratory outcomes

Label these separately. Include the planned multiplicity adjustment (the guard
against many secondary comparisons manufacturing a chance finding) and never
use a secondary result to rewrite the primary conclusion.

## Trace and prompt audit

Show the condition-manifest diff, invariant-check outcome, tool-schema diff,
and a small condition-blinded sample of traces. Record any contamination or
protocol deviation.

Also state what every condition actually received: summarize the rendered
prompt/tool diff and link the content-addressed bundle. A *trace* is the
chronological record of prompts, model messages, tool calls, and tool results.

## Interpretation

Separate what the cohort establishes from what it suggests. State limits on
generalization across tasks, model snapshots, temperatures, frameworks, and
agent loops. Link the next registered experiment rather than retroactively
tuning this cohort.
