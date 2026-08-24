# Current Assist baseline final local review

The final local review verified the sealed v7 bundle, one admitted model request,
raw request-capture hash, reason-coded recursion-limit outcome, record seals,
and result report. The deterministic suite passed (16 tests).

## Deferred findings

The reviewer found six real improvements. They do not change the already
recorded v7 failure and each would broaden this first pass into a reusable
runner/security redesign or require a new registration and a second model run.
They are deferred under the explicit rescope, not rejected as false.

1. Kill a whole admitted process group on parent timeout. Risk: a future timed
   out worker could outlive the parent admission wrapper. Value: bounded shared
   model ownership. This needs a shared-wrapper/process-lifecycle design.
2. Replace the worker's environment marker with an admission capability the
   wrapper can attest. Risk: a local maintainer can invoke the private worker
   module directly. Value: enforce no direct-model execution by construction.
   This needs a shared-wrapper contract, not a one-study patch.
3. Seal and compare complete provider tool schemas before a future request.
   Risk: a later changed schema could be mislabeled as the same setting. Value:
   valid controlled comparisons. V7 captured its actual schemas locally, but a
   reusable pre-registration schema-extraction design is separate work.
4. Seal the resolved tag commit ID, not just its name. Risk: a force-moved tag
   could defeat the local identity check. Value: stronger historical anchoring.
5. Require a clean Assist source tree or seal its imported-tree digest. Risk:
   uncommitted source changes could alter a future run. Value: exact harness
   reproducibility across workers.
6. Make a successful note oracle require the whole expected file, not only one
   exact requested line. Risk: a future successful run could retain unrelated
   extra content. Value: stricter artifact success.

These belong in a follow-up runner-hardening registration. No model rerun,
product change, or treatment change is authorized by this review.

## Rebase integration review

After the baseline branch was rebased onto the merged scripted-MVP harness, it
became clear that the MVP seals every top-level `harness/*.py`. Keeping an
unrelated real-model runner in that module set would make its already sealed
static fixture fail closed. The final branch therefore stores the self-contained
v7 result capsule; its executable source remains at the immutable v7 tag. This
leaves the MVP bundle, the v7 bundle, the captured Assist revision, and all v7
result records unchanged.

The archived v7 episode remains reproducible from its own tag. It must not be
rerun from this integrated branch: the registration's source-binding guard
correctly rejects a changed runner, and any future real episode needs a new
registered study version. Its bundle predates the current shared bundle schema,
so the capsule preserves its original bytes and verifies them through that tag,
rather than rewriting the executed registration. The integrated deterministic
suite passed 35 tests, with `compileall` and `git diff --check` also clean.
