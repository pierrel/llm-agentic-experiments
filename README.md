# llm-agentic-experiments

A controlled research lab for studying how prompt placement, repetition, and
progressive guidance affect small models acting as agents.

This is not an Assist release repository. It may borrow a *shape* from Assist:
an agent loop, filesystem-like state, progressive skill loading, tool calls, and
specialist-task handoffs. It must not become a hidden fork of Assist or a path
for shipping unvalidated prompting changes.

The project has two jobs:

1. Run preregistered, contamination-resistant experiments.
2. Make the evidence easy to inspect: a captured prompt, tool trace, oracle
   result, model configuration, and analysis are one durable experiment record.

The initial research plan is [docs/0001-agentic-guidance-experiments.md](docs/0001-agentic-guidance-experiments.md).
The operating and review contract is [AGENTS.md](AGENTS.md); the full document
map is [docs/README.md](docs/README.md). The initial setup and review record is
[docs/0000-initial-documentation-report.md](docs/0000-initial-documentation-report.md).

## Non-negotiable rules

- Every real model run goes through the shared admission wrapper:

  ```sh
  /home/pierre/src/agentic/tools/agentic resource run llm -- <bounded command>
  ```

  No direct local-model or GPU command is permitted. One trial is one bounded
  admission, so production can regain the slot between trials.
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

## Local checks

The integrity kernel intentionally needs no third-party package:

```sh
python -m unittest discover -s tests -v
python -m compileall -q harness tests
```
