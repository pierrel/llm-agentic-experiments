# V8 confirmation: retrieved guidance helped under the largest context dose

## Result

V8 completed all 72 preregistered episodes. It compares the same procedure in
two forms: G01 places it in the system context; G02 offers a matching skill
description and requires the agent to load the procedure. Each form ran 12
fresh private Deep Agents episodes at each of three inert-context doses.

| Context dose | Handed G01 | Retrieved G02 |
| --- | ---: | ---: |
| Low | 12/12 | 10/12 |
| Medium | 8/12 | 9/12 |
| High | 5/12 | 11/12 |
| Total | 25/36 | 30/36 |

The evidence supports a narrower version of the hypothesis: on this task,
retrieved guidance did better once the context was large. It does not support
the claim that retrieval is always better. At the low dose, handing over the
procedure did better.

## Design and evidence

This is the fresh Northridge Labs equipment-return task, using Qwen3.8 with
reasoning enabled, the current Assist request profile, and the Deep Agents
filesystem/tool loop. G01 and G02 share the task, tool schema, model settings,
schedule, and context dose. The outcome is a condition-blind deterministic
check of ordered record reads and a fixture-grounded handoff. All failures,
including 17 artifact failures, remain in the result.

The sealed result capsule is
`results/reach-for-instructions-confirmation-v8-qwen38-current-r3/`. Its
bundle digest is
`13f853ad3c04150741c8a94a8f4dd8afb5c2eeeeb7a4666b2ead5a0d12cf5044`.
Raw traces remain private; their hashes, admission chain, outcome chain,
settings, and aggregate report are committed in the capsule.

## What was hard

V7 was intentionally stopped after 13 outcomes because its oracle rejected a
grounded compact approval form that the task did not require the agent to
expand. V8 used a new task and a pre-admission calibration corpus. Copilot
then found genuine false-accept paths in the V8 oracle: contradictory
completion wording, compact confirmation variants, identifier boundaries, and
unsupported claims in non-status fields. Those were fixed and resealed before
the first V8 request. The full cohort therefore uses the corrected r3 oracle.

## Learning and next step

The learning is a response surface, not a delivery-mode verdict: retrieval may
help the model recover a procedure from a crowded prompt while adding needless
friction to a quiet one. The matching private blog seed is
`larochelle.io/seeds/2026-09-11-retrieval-helps-under-pressure.org`.

The proposed next experiment holds the task and current setting fixed, adds
more context doses around V8's high-context region, and then repeats on a
fresh task family. The generated capsule includes the proposed Assist roadmap
item. No Assist guidance or architecture change is authorized by this result.

## Verification and review

- The experiment suite passed: 114 tests.
- The final result capsule passed `git diff --check` and a local evidence,
  privacy, design-adherence, and documentation review.
- Copilot’s two meaningful V8 review rounds were addressed before admission;
  the next round produced no new review. One suggestion to treat the local
  shared-GPU wrapper as a model-provider trust boundary was declined and
  resolved: it is cooperative scheduling, not access control, and hardening
  that boundary would be separate work.
