# Reach-for-instructions V7 integrity re-review

V6's completed records exposed four P1 review findings: the current callback
path did not retain the provider request, no post-callback request contract was
enforced, a timeout could leave a worker outside the admission wrapper, and the
sealed hypothesis-seed path was absent from this branch. V6 remains archived but
invalid for interpretation.

- **Scientific integrity:** V7 copies the final V6 task, conditions, response
  surface, schedule, settings, and artifact oracle unchanged. It is a fresh
  validation execution, not another result-informed treatment or scoring change.
  The seed is now committed at its sealed path. The runner captures the actual
  model-boundary request, and refuses an episode whose captured prompt, tool schema,
  fixture identity, or decoding values differ from the sealed descriptor.
- **Statistical rigor:** V7 retains 18 fresh episodes, three per context-by-
  delivery cell, the same deterministic interleaving, and reason-coded terminal
  outcomes. It may validate runner fidelity, but it remains development-only and
  cannot produce a stable effect estimate or product decision.
- **Agentic harness fit:** a no-provider interception renders each trial's
  actual first post-middleware Deep Agents request, including its final message
  content blocks and invocation parameters. The per-trial digest is stored
  before sealing. The live model boundary captures its first `_generate` call
  and compares it exactly against a freshly rendered request whose digest must
  equal the sealed digest. The descriptor independently checks its full fixture
  digest. A missing or drifted capture is a provider error, and stops the cohort
  after that recorded outcome rather than permitting later incomparable
  episodes. Timeout cleanup starts each admitted command in a new session,
  terminates that whole process group, waits, and escalates to `SIGKILL` before
  the schedule advances.
- **Minimum adequate setup:** no agent capability, treatment text, task,
  context amount, model, or replicate was added. The new capture, fidelity
  check, source seed, and process-group cleanup are measurement and containment
  requirements, not experimental scope.

The unit suite exercises missing and drifted request evidence. The live cohort
is self-probing: its first episode cannot be scored or allow a later episode
unless the actual model boundary supplies the exact sealed provider request.
