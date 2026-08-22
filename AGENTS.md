# Research repository guide

This repository is a laboratory for learning about agentic prompting. It is not
an Assist implementation branch, a benchmark leaderboard, or a route for
shipping a favorable prompt experiment.

## Working agreements

- Any claim or recommendation that a prompt, skill, tool, or other mechanism
  should change model behavior begins as a dated file under `seeds/`. Capture
  the intervention, predicted observable outcome, boundary/counterexample, and
  originating context. It is a hypothesis seed, not evidence, a preregistration,
  or authorization to change Assist. Keep rejected product ideas too: repeated
  seeds reveal patterns worth testing.
- A study begins with a committed registration under `experiments/<study>/`.
  It names the hypothesis, conditions, task split, model/configuration, sample
  plan, exclusions, randomization seed, primary outcome, and analysis script.
  Amendments are new dated files. Never rewrite a registration after model
  results exist.
- Conditions must differ only in declared factors. The runner must capture and
  compare the rendered provider prompt, tool schemas, fixture digest, model
  request, and decoding configuration before it admits a trial.
- Preserve failures, refusals, timeouts, and interrupted model episodes. They
  are outcomes, not cleanup candidates. A GPU admission denial happens before a
  model request, so it is an administrative attempt under the same scheduled
  trial ID. Record it separately and retry that episode before advancing the
  registered order.
- Keep a development task set separate from the locked confirmation set. Any
  change informed by development results starts a new registered version.
- Primary outcomes are deterministic whenever possible. Any qualitative review
  is blinded to condition and uses a committed rubric.
- Never put a task-specific expected tool, path, fixture name, or oracle phrase
  in a natural user prompt or treatment guidance.
- A confirmation registration declares its experimental unit, exact primary
  contrast, fixed sample size/power rule, missingness/retry policy, and analysis
  script hash before treatment labels are revealed. Every scheduled episode is
  counted with a reason-coded outcome.
- Before the first model request, tag a content-addressed study bundle containing
  the registration, condition manifests, task bank, schedule, fixtures, tool
  schemas, runner/dependency revisions, and analysis plan. The runner fails
  closed if any declared hash changes. Results append to a hash chain; an
  amendment receives a new study ID rather than rewriting an executed plan. A
  local chain/seal detects accidental edits, but the real runner must bind the
  bundle digest to an immutable git commit/tag before admission.

## Model and GPU use

Every real-model run must use the shared workspace admission wrapper:

```sh
/home/pierre/src/agentic/tools/agentic resource run llm -- <one bounded trial>
```

Do not invoke llama.cpp, a local OpenAI-compatible endpoint, CUDA, or another
GPU command directly. The runner must have no direct-model escape hatch. On an
admission denial, record the attempt and continue non-model work; do not poll,
sleep-loop, or reserve the slot.

## Required design review

Before any registered study receives model results, obtain and resolve written
reviews through at least these lenses:

1. **Scientific integrity:** contamination, blinding, preregistration,
   reproducibility, and researcher degrees of freedom.
2. **Statistical rigor:** experimental unit, sample/power plan, randomization,
   missingness, multiplicity, and interpretation.
3. **Agentic harness fit:** agent loop, tool semantics, prompt assembly,
   fixture isolation, and trace/oracle validity.

Each review identifies verified findings. Fixes and declined findings live in
the study's design record before the first trial. Re-review after any material
design change.

## Integrity self-tests and registry

The harness must test its own guards before real-model use. Deliberately add an
undeclared prompt, schema, fixture, or decoding difference; omit a scheduled
trial; leak a condition label; and alter a stored result record. Validation must
reject every case.

`docs/study-registry.md` records every study version and whether it is design,
development, pilot, confirmation, superseded, or reported. It is an index, not
permission to overwrite an earlier registration.

## Repository boundaries

Commit study definitions, analysis code, aggregate tables, generated figures,
and compact redacted example traces. Keep raw prompts and traces local by
default: they can be large and may accidentally contain operator context.
Never use real user data, current Assist threads, live network access, or a
production filesystem as a fixture.
