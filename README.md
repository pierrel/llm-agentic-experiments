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
Product guidance claims first enter [seeds/](seeds/) as hypotheses, then earn a
registered study if they are worth testing.

The current [MVP roadmap](roadmap.org) covers the sealed, scripted no-model
harness. It validates the measurement path only; real model trials remain
deferred until a registered study and its design reviews are complete.

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
- Experiments test **when**, not only **if**, a hypothesis holds. Each
  registration identifies its quantitative design axes, records their actual
  values per episode, and predeclares whether it estimates a response curve,
  threshold, or condition interaction. Report where an intervention helps, has
  no detectable effect, or harms; do not reduce a dose-response to a
  short-versus-long headline. Context length, task complexity/length, and
  skill-catalog size are common axes. First-class treatment does not require an
  unpowered full factorial: hold non-primary axes fixed and measured, then add
  them through separately powered registrations.
- Every trial starts from a fresh conversation and isolated fixture. It receives
  no prior trial output, result label, or tuning note.
- Use deterministic artifact oracles where possible. Human or model judging is
  blinded to condition and recorded separately.
- A result is exploratory until it has a held-out confirmation cohort. Do not
  tune a treatment on that cohort.

## Direction, development, and confirmation

After a behavioral claim has been captured as a [seed](seeds/README.md), Pierre
may give only the general direction for the experiment. The experiment agent
turns it into the minimum adequate development study and a sealed development
registration. If a completed development version shows no detectable
difference, it creates and fully reviews at least two further
defensible development versions, for three total where feasible. The initial
development plan states the eligible axes and the feasibility, safety, and
resource boundaries that may stop the series earlier. Each version has its own
committed registration and completes every required design-review lens before
model trials. It retains its task, settings, schedule, results, and null
finding. Never alter a completed registration or repeat its completed model
cohort to manufacture a difference. Retrying an admission-denied episode under
its unchanged sealed registration remains required.

For first experiments and other high-touch work, Pierre reviews the task and
oracle, context or treatment schedule, and registration before model trials.
That feedback calibrates the process. Later work can proceed from broad
direction while preserving the same checkpoints as inspectable artifacts.

When multiple subagents are available, control their context: a design role
gets Pierre's direction but not scored condition results; implementation gets
the frozen registration; scoring gets opaque condition IDs and deterministic
oracle output; iteration gets only permitted aggregate development evidence.
Confirmation uses held-out tasks and is never tuned after results appear.

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
A genuine learning gets a private `larochelle.io/seeds/` blog seed linked to the
capsule and a proposed Assist roadmap item. These are evidence-preserving
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
