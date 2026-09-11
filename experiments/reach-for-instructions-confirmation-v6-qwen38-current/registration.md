# Reach-for-instructions held-out confirmation V6: current Qwen 3.8 profile

## Question and contrast

Does a procedure-heavy natural equipment-return task complete more often when
the agent discovers and loads a matched procedural guide than when the complete
procedure is already in system context? The model, private workspace, fixture,
filesystem/tool loop, temperature, context dose, and loader schema are fixed.

G01 receives the full procedure in system context. The fixed `load_skill` tool
schema remains present, but the prompt does not expose any guide name or catalog
entry. G02 receives only the exact guide catalog entry; the same procedure is
available only after it calls `load_skill(prepare-equipment-return)`. This
makes discovery versus already-present guidance the declared treatment instead
of allowing G01 to silently reproduce G02's named discovery path.

## Settings and task split

The experimental unit is one fresh private Deep Agents episode on the new
Dockside Transit equipment-return fixture. Cedar Loop V5 is not reused: its
results informed this new task and calibration, so it remains a separate
reported capsule. Qwen3.8 uses current Assist's explicit profile: temperature
0.1, reasoning enabled, the server-reported 131,072-token context window, and
no client `max_tokens` request field. The 20-turn recursion limit remains the
minimum run-safety bound for this compact task, not an Assist product setting.

Three inert system-context doses remain fixed quantitative strata: 0, 900, and
3,600 lines. The delivery surface changes prompt length by design; that is the
mechanism under test rather than an uncontrolled task or tool difference.

## Sample, randomization, and missingness

The schedule contains 12 fresh trials for each delivery-by-dose cell: 72 total.
The randomization seed is `20260911`; positions are interleaved in opaque G01/G02
pairs and analysis adjusts for schedule position descriptively. A denied shared
GPU admission is retained as an administrative attempt and retries the same
trial. Every admitted terminal result, including provider errors and timeouts,
is reported without replacement.

## Outcomes and analysis

The primary outcome is a deterministic, condition-blind, fixture-grounded JSON
handoff plus required inventory/read/write ordering. The independent calibration
corpus must accept an unresolved statement that asks which label is attached to
the kit and reject both a direct unsupported attachment assertion and an
unsupported completed-return claim before any model request. The secondary
process measure is an exact named-skill call before the first source read; it is
computed even when the primary artifact fails.

Report every terminal outcome, condition-by-context cell count, actual
first-provider-request input tokens, and the secondary process count. Do not
infer a global delivery effect, a context threshold, or transfer beyond this
model/profile/harness/task from one confirmation.
