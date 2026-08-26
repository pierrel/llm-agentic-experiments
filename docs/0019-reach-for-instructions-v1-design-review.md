# Reach-for-instructions v1 design review

This review was completed before any model request for
`reach-for-instructions-dev-v1`.

## Scientific integrity

The seed is `seeds/2026-08-24-reach-for-instructions.md`. The registration fixes
the two whole-policy conditions, fixture, filler amounts, schedule seed,
primary oracle, and interpretation rule before outcomes. The skill body is
identical in both arms and remains callable in the handed arm, so the treatment
does not remove a capability. Raw traces retain opaque condition IDs; scoring
does not inspect the condition.

Finding resolved: a prose handoff oracle would repeat the phrase-equivalence
problem exposed by the previous context-length development work. V1 instead
requires a declared JSON structure and exact fixture-grounded values, while
allowing natural wording only in the separate final response.

## Statistical rigor

The experimental unit is one fresh agent episode. Eighteen episodes give three
development observations at each delivery-by-context cell. That is insufficient
for a confirmatory effect estimate; it is adequate to find broken treatment
delivery, gross harm, or a promising response-surface region worth a held-out
cohort. The schedule interleaves conditions and rotates their position as far
as three blocks permit; the report retains order and every reason-coded outcome.
There is no early stopping or outcome replacement.

Finding resolved: do not describe the three replicates as powered confirmation.
The registration and report label them development-only.

## Agentic harness fit

The runner uses the current Deep Agents filesystem loop, a fresh virtual
filesystem, and one `load_skill` tool. The user request does not name a skill,
tool, output path, fixture record, or oracle phrase. The catalog description is
available in both arms; success in the reached arm without loading is retained
as a meaningful whole-policy outcome. The procedure oracle requires inventory,
all source reads, then write, and source immutability.

Finding resolved: procedure delivery is deliberately not conflated with a
different tool schema. Both arms receive the same callable tool and body.

## Minimum adequate setup

One task, two delivery modes, three context doses, and three replicates are the
smallest setup that tests the stated response surface. No subagents, network,
retrieval, real workspace, additional skills, semantic judge, or second task
axis is included. The depth of the task is sufficient to make the procedure
observable, but no artificial obstacle is introduced solely to force a result.
