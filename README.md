# llm-agentic-experiments

A controlled research lab for studying how prompt placement, repetition, and
progressive guidance affect small models acting as agents.

The project has two jobs:

1. Run preregistered, contamination-resistant experiments.
2. Make the evidence easy to inspect: a captured prompt, tool trace, oracle
   result, model configuration, and analysis are one durable experiment record.

The initial research plan is [docs/0001-agentic-guidance-experiments.md](docs/0001-agentic-guidance-experiments.md).
The operating and review contract is [AGENTS.md](AGENTS.md); the full document
map is [docs/README.md](docs/README.md). The initial setup and review record is
[docs/0000-initial-documentation-report.md](docs/0000-initial-documentation-report.md).
Product guidance claims first enter [seeds/](seeds/) as hypotheses, then earn a
registered study if they are worth testing.

The current [MVP roadmap](roadmap.org) covers the sealed, scripted no-model
harness. It validates the measurement path only; real model trials remain
deferred until a registered study and its design reviews are complete.

## Non-negotiable rules

- A treatment and control differ only in the preregistered factor. Their model,
  decoding settings, tools, fixture, synthetic time, user task, and outcome
  oracle are identical.
- Every trial starts from a fresh conversation and isolated fixture. It receives
  no prior trial output, result label, or tuning note.
- Use deterministic artifact oracles where possible. Human or model judging is
  blinded to condition and recorded separately.
- A result is exploratory until it has a held-out confirmation cohort. Do not
  tune a treatment on that cohort.

## Planned layout

```text
experiments/       preregistered study definitions and condition manifests
fixtures/          hermetic agentic tasks, tools, and synthetic data
harness/           runner, prompt capture, trace capture, randomization, storage
analysis/          locked analysis scripts and generated figures/tables
results/           append-only local records, seals, manifests, and reports
docs/              study designs, decisions, and research log
```

The first implementation milestone is the harness, not a prompt rewrite.

Each sealed run records three independent axes: test fixture, model, and
harness architecture. A generic JSON `settings` object records every
behavior-affecting option, including reasoning controls. This keeps an exact
test reusable across a new model or an alternative architecture without
mislabeling the resulting bundles as one cohort.

## Result history and learning handoffs

Archive every completed run in `results/<run-id>/`. A result capsule commits the
sealed bundle and settings, admission/outcome chains and seals, report, and the
hash inventory for locally retained raw traces. It also contains `learning.md`
for the observation, evidence, and limits, plus `assist-roadmap-proposal.md`.
A genuine learning gets a private blog seed linked to the capsule and a proposed
Assist roadmap item. These are evidence-preserving
handoffs, not authorization to change Assist.

## Local checks

The integrity kernel intentionally needs no third-party package:

```sh
python -m unittest discover -s tests -v
python -m compileall -q harness tests
```

To prove the committed synthetic fixture end to end, use a private local
artifact directory. It writes bundle, trace, record, seal, and aggregate-report
artifacts and makes no model, GPU, network, or Assist request. Repeating the
same command verifies the sealed artifacts rather than rerunning them:

```sh
python -m harness.demo /tmp/llm-agentic-experiments-mvp
```
