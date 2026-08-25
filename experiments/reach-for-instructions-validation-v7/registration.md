# Reach-for-instructions validation registration v7

V6 completed its screen but the post-run local review found that the runner did
not retain the provider-facing request through the callback used by this runtime
and did not reject a fidelity mismatch before recording an outcome. V6 remains
archived as an invalid-for-interpretation run. V7 is a clean validation rerun
after those runner integrity fixes.

V7 changes no experimental variable from V6: it uses the same reimbursement
fixture, natural user request, opaque delivery conditions, three context doses,
18-episode interleaved schedule, model, reasoning setting, Deep Agents loop,
decoding, tools, skill body, and calibrated deterministic artifact oracle. The
only change is that the runner now renders each actual post-middleware provider
request without calling the model, seals its per-trial digest, compares the
actual model-boundary request against that exact request, and terminates the
whole worker process group on timeout before the next trial can begin.

This is not a third result-informed treatment change. It is the required first
valid execution of the final, already chosen measurement setup. Its findings
remain development-only and are not evidence for an Assist product change.

## Independent immutable plan

- **Experimental unit:** one fresh agent episode in a new private filesystem.
- **Conditions:** opaque `G01` hands the procedure in system context; opaque
  `G02` supplies the same catalog and tool but loads the same procedure on
  request. No capability is removed from `G01`.
- **Tasks and sample:** `C-low`, `C-medium`, and `C-high` use 0, 900, and 3600
  inert filler lines. Three new episodes per delivery-by-context cell make 18
  episodes. The schedule uses randomization seed `20260825`, interleaves paired
  condition blocks, and declares `adjust_for_position` for the three-block
  remainder.
- **Runtime:** the pinned Qwen3.6-27B Q4 model, reasoning disabled,
  temperature 0.1, 1,200 output tokens, current pinned Assist Deep Agents loop,
  and the same no-caller-tools/no-subagents fixture setup as V6.
- **Primary outcome and exclusions:** a condition-blind deterministic oracle
  requires one grounded JSON handoff, source immutability, workspace inventory,
  and every source read before writing. Every admitted terminal episode is kept
  with its closed reason code. A denied admission retries the same scheduled
  trial before the schedule advances; there are no post-result exclusions or
  early stops.
- **Analysis:** `studies/reach_for_instructions/runner.py`, sealed by its
  implementation digest in `bundle.json`, reports reason-coded outcomes and
  actual first-request tokens by delivery and context cell. It makes no effect
  estimate beyond development screening.
