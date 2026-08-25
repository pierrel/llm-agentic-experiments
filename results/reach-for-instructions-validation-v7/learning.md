# V7 learning: retrieved guidance is promising here, but the context surface is not established

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

All 18 admitted episodes passed the sealed provider-request contract, so this
is the first interpretable run in the development series. The complete
artifact oracle passed in 5 of 9 retrieved-guidance (`G02`) episodes and 2 of 9
always-present-guidance (`G01`) episodes.

| Inert context dose | Always present `G01` | Retrieved `G02` |
| --- | ---: | ---: |
| 0 lines | 0/3 | 1/3 |
| 900 lines | 0/3 | 1/3 |
| 3,600 lines | 2/3 | 3/3 |

The outcome supports a narrow development observation: on this reimbursement
task and this exact current-Assist setup, letting the agent retrieve the same
procedure did not hurt and produced more complete handoffs overall. It does
not show that retrieval helps *because* context is long. Both conditions
improved at the largest dose, and the treatment-control gap is only one episode
in every individual context cell. The run therefore does not establish a
threshold, a monotonic context effect, or a product rule.

## Limits

Three fresh episodes per cell are a development screen, not a stable effect
estimate. The single task, one procedure, one skill description, one model with
reasoning disabled, and one Deep Agents harness cannot establish transfer to a
new task, model, reasoning setting, harness architecture, or skill catalog.
The treatment loaded the skill before the first source read in 5 of its 9
episodes; that process measure is useful diagnostic evidence, but not a causal
isolation of the loaded-message channel.

## Handoffs

A private `larochelle.io` seed records the surprising constraint: a result can
look directional without yet telling us where it applies. The next laboratory
step is a preregistered held-out task confirmation with a larger per-cell sample
and a preflight oracle-calibration gate. `assist-roadmap-proposal.md` records
that proposal. Neither handoff authorizes an Assist change by itself.
