# Durable-promise capability routing v1: pre-result design review

## Scientific integrity

**Finding:** The old reported holdouts were observed repeatedly and cannot be
called untouched confirmation data. The old driver did not seal requests,
schemas, settings, schedule, or raw-trace hashes.

**Resolution:** Preserve the old registration, report, and frozen eval commit
as exploratory lineage only. Use all five old rows for development diagnostics,
lock new confirmation rows before admission, use opaque condition IDs and a
condition-blind deterministic oracle, and archive every reason-coded outcome.

**Finding:** Editing several skill descriptions together would obscure which
change caused an effect.

**Resolution:** This version changes one general grounding-description boundary
only. A package-level capability-boundary treatment is a future study, not an
unreported extension.

## Statistical rigor

**Finding:** Full-row pass conflates route/lifecycle, durable commitment, and
answer/honesty; a routing treatment could change one without the others.

**Resolution:** Record R, P, A, and F = R ∧ P ∧ A per episode. R is the causal
primary; F is the product primary. P conditional on R is diagnostic only.

**Finding:** N=3 can screen an engineering candidate but cannot support a
release inference.

**Resolution:** N=3 per condition/task is development screening. Fixed
confirmation is N=14 per condition across four new rows, 112 fresh episodes.
The release gate uses effect direction, worthwhile improvement, confidence
intervals, and fixed regressions rather than a blanket 70% threshold.

## Agentic harness fit

**Finding:** The sealed scripted harness and the existing one-episode real
pilot omit the ordinary web-main skills, async context lifecycle, sandbox, and
private `/agent` state. They cannot faithfully execute these rows.

**Resolution:** Build a study-specific adapter from the frozen EDD trajectory:
the actual `create_agent` web-main graph, deterministic context fixture, exact
completion wake, network block, and private-memory plus tool-order oracle.
Capture all rendered provider requests and schemas before each model call.

## Minimum adequate setup

**Finding:** A generic replacement for the full Assist runner would expand this
study beyond its causal question, while raw chat or a filesystem-only loop
would lose material behavior.

**Resolution:** The adapter supports only this sealed task family and delegates
all model admission to the shared wrapper one episode at a time. It has no live
network, user data, production state, extra planner, or alternate model. The
current `time-skill-routing` branch remains a fixed external dependency, not
an unrecorded treatment factor.
