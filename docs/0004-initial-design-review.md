# Initial design review and resolutions

Date: 2026-08-20. This record captures the required reviews before any real
model run. No experiment has been executed.

## Scientific integrity

The review found that the original Study A mixed two questions: whether a rule
was repeated and whether it appeared near the action. It now uses a
token-matched 2×2 system-slot × skill-slot design, including both a local-only
and a neither-rule control. The review also required an explicit whole-policy
definition for Study B, a complete task bank before piloting, real blinding
limits, sealed preregistration bundles, a study registry, and guard self-tests.
All are now specified in Design 0001; the starter harness already enforces the
bundle, schedule, and record-chain parts. Its remaining guard self-tests ship
with the real-model runner. Conclusions are restricted to the pinned model,
loop, task bank, and decoding regime.

## Statistical rigor

The review required an explicit episode-level unit, blocked interleaving,
seed-support calibration, a pilot that cannot become confirmation evidence, a
minimum worthwhile effect, fixed confirmation N, an all-scheduled
intention-to-treat denominator, and a named primary contrast. Design 0001 now
does this. The first task matrix is treated as fixed strata, not a sample from
all possible agent tasks. Artifact success is Study B's only shared primary;
skill-loading behavior is diagnostic.

## Agentic harness fit

The review required exact Study B delivery timing and message role, unchanged
tool availability after automatic delivery, full multi-turn request capture,
hermetic virtual tools, and a deterministic artifact predicate independent of
the condition. The design now defines automatic delivery as a fixture-owned
system-context message before the first decision and treats the contrast as a
whole policy. The first harness code is deliberately a small purpose-built
loop, not DeepAgents: its job is control, while a future compatibility fixture
can verify the declared affordance shape against Assist.

## Preconditions before a real model run

The starter harness is not yet a real-model runner. Before one is added, it
must bind the content-addressed bundle digest to an immutable git commit/tag,
record seed-support calibration before asking for shared generation seeds, and
use the existing invariant and review-packet checks against real rendered
multi-turn provider requests. The local hash chain is tamper-evident storage,
not a substitute for that immutable registration identity.

## Plain-English scientific editor

The review found that the design used research vocabulary before showing the
basic model-tool-checker loop. The documentation now has a plain-language
opening, a short glossary, an invented walk-through, reader order, and required
plain-language registration and result sections. Technical terms remain where
they carry a precise commitment, but their practical consequence is stated
nearby.

## Remaining intentional limits

This commit does not implement a provider client, real-model executor,
tokenizer adapter, statistical analysis package, or dashboard. Those would
create run-time policy and operational surfaces that need a study-specific
implementation plan. The sealed bundle, schedule, and record-chain interfaces
are the foundation those pieces must use; their self-tests run without the GPU.
