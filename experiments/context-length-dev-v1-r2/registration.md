# Context-length instruction-following development registration v1, runtime-source revision

This supersedes the unrun `context-length-dev-v1` bundle. That bundle remains
sealed and unmodified; its deployment-tree preflight could not establish the
claimed Assist Git revision, and it produced no model result.

The question, fixture, natural user request, conditions, decoding, model
weights, and deterministic oracle are unchanged. The worker now imports Assist
from a clean worktree at the sealed revision, using the deployment virtualenv
only for its pinned Python dependencies. Before invocation it verifies that
worktree's Git revision, clean status, package versions, served model ID, and
reasoning switch.

The three fresh episodes run in deterministic pseudorandom order from seed
`20260825`. The provider-reported first-request `input_tokens` is the realized
dose. This remains a three-episode development screen. If it shows no
detectable difference, the next two development registrations must be fully
reviewed and sealed before their model runs.
