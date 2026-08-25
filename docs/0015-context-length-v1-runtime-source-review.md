# Context-length v1 runtime-source revision review

Date: 2026-08-25. The original v1 bundle was not run because its preflight
correctly rejected a copied deployment source tree with no Git revision.

The revised worker changes only provenance enforcement. It imports Assist from
an explicit clean Git worktree and verifies the sealed commit before a model
invocation. The deployment virtualenv remains the dependency provider. The
fixture, three filler levels, order seed, oracle, model weights, reasoning
setting, and loop configuration are unchanged.

This is the minimum correction that makes “current Assist revision” observable
rather than asserted. It does not tune the task or analyze an unadmitted
preflight failure as a behavioral outcome.
