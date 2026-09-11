# Reach-for-instructions held-out confirmation V8: approval-status representation correction

## Why this is a new study

V7 ran 13 terminal current-Qwen3.8 episodes, all rejected by its primary
oracle. The handoffs preserved the source facts in the compact approval-status
form `conditionally_approved_pending_intake_photo`. V7's preregistered corpus
also required supervisor Maren in that field, although the requested output did
not ask for a supervisor. V7 remains a partial, non-diagnostic execution and is
not amended or pooled with V8.

V8 uses a fresh Northridge Labs fixture and a condition-blind calibration. It
accepts either a direct status explanation or the compact form when it records
conditional approval and a still-pending intake photo. It rejects a bare
approval, a photo already confirmed, invented receipt/completion, and an
unsupported label-attachment assertion.

## Question and contrast

Does a procedure-heavy natural equipment-return task complete more often when
the agent discovers and loads a matched procedural guide than when the complete
procedure is already in system context? The model, private workspace,
filesystem/tool loop, temperature, context dose, loader schema, and task shape
are fixed within V8.

G01 receives the full procedure in system context. The fixed `load_skill` tool
schema remains present, but the prompt does not expose any guide name or catalog
entry. G02 receives only the exact guide catalog entry; the same procedure is
available only after it calls `load_skill(prepare-equipment-return)`. Discovery
versus already-present guidance is the declared treatment.

## Settings, design, and outcome

Each unit is one fresh private Deep Agents episode. Qwen3.8 uses current
Assist's profile: temperature 0.1, reasoning enabled, the server-reported
131,072-token context window, and no client `max_tokens` request field. The
20-turn recursion limit is a run-safety bound, not an Assist product setting.

The schedule contains 12 fresh trials for each delivery-by-dose cell: 72 total.
System-context doses are 0, 900, and 3,600 inert lines; seed `20260913`
interleaves opaque G01/G02 pairs. A denied shared-GPU admission is retained as
an administrative attempt and retries the same trial. Every admitted terminal
result, including provider errors and timeouts, is reported without replacement.

The primary outcome is a deterministic, condition-blind, fixture-grounded JSON
handoff plus inventory/read/write ordering. The secondary process measure is an
exact named-skill call before the first source-record read, computed even when
the primary artifact fails. Report every terminal outcome, condition-by-context
cell count, actual first-provider-request input tokens, and the secondary
process count. Do not infer a global delivery effect, a context threshold, or
transfer beyond this model/profile/harness/task from V8 alone.
