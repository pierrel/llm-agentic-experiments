# V5 execution record: valid cohort, no conclusion about guidance delivery

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

All 72 scheduled trial identities, their captured provider requests, traces, and
terminal records verify against sealed bundle
`9fcb081c79f9fa606ffdc2eb321aa7a493970a51b9a86c00a7ce07a1a26734c8`.
The 73 admissions consist of those 72 terminal trials plus one retained
production-busy refusal. The final seals verify the complete schedule and all
72 raw-trace hashes.

The registered 900-second operational batch break was bypassed after trial 53:
the adjacent traces are 138 seconds apart. Pierre explicitly classified that
as an operational deviation, not a treatment or experiment-validity variable.
It is retained here for reproducibility but does not invalidate this cohort.

The primary report has 72/72 `artifact_failure` outcomes, evenly split as 36
per opaque condition and 12 per context-by-condition cell. That is not an
effect estimate. Raw-trace review shows every handoff describes the badge tag
as unresolved, for example “records do not establish which tag is attached to
badge B-77.” The calibrated oracle rejects every such handoff because its
negative-evidence filter rejects the word `attached` even in that unresolved
construction. This is a result-observed false-negative boundary; it must not
be patched and retroactively rescored in V5.

The raw traces also show `load_skill(prepare-access-transition)` before the
first source read in all 36 G01 and all 36 G02 episodes. The stored secondary
field says `false` because scoring returns on the primary oracle failure before
it visits tool calls. The control therefore reached for the same guide as the
treatment, so V5 did not produce the intended behavioral delivery contrast.

## Limits

V5 is faithful to the pinned Assist revision `45762e5831a5c656a68677cbb6f43338eb954e0c`:
Qwen 3.8, temperature 0.1, reasoning disabled, 1,200 output tokens, and the
sealed Deep Agents loop. Current Assist `main` now defaults Qwen 3.8 reasoning
on and ordinary threads do not impose that 1,200-token cap. V5 is therefore a
valid record of its own settings, not a result for the current main profile.

No effect estimate, cell comparison, or product inference from V5 is durable
evidence. It does not establish transfer across tasks, models, harnesses, or
reasoning settings.

## Handoffs

The follow-on must be freshly preregistered. Before any admission it needs to:

1. Calibrate the oracle with the observed unresolved `attached` construction
   and a matched unsupported assertion, without rescoring V5.
2. Record skill-load timing even when the primary artifact fails.
3. Specify a delivery design that makes a control’s access to the guide and
   expected behavioral contrast explicit, since both V5 arms loaded it.
4. Use an explicitly chosen current Assist model profile, including reasoning
   and output-token policy.

This is a laboratory-method finding, not a blog seed or an Assist product
proposal.
