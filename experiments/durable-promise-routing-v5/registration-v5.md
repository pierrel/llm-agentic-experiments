# Durable-promise capability routing v5

Status: registered pilot. No model episode has run in this version.

V5 is the clean successor to the preserved exploratory work and v1-v4
pre-request infrastructure events. None produced a provider request, tool call,
agent response, or baseline observation. Their versioned private evidence is
retained and is never replayed.

The scientific question, four natural pilot rows, counterbalanced 24-episode
C0/C1 schedule, R/P/A/F observables, and count-only advance rule are unchanged
from v4. `C0` is the exact current grounding description. `C1` adds only this
general boundary: “A question about the user's own date, time, meeting,
deadline, or status needs this skill when the answer comes from their records.”
No model-visible prompt, skill, schema, tool, fixture, model, or scoring change
is introduced by this successor.

The only harness correction passes the original virtualenv interpreter path to
the admitted worker rather than resolving its symlink to the system Python. V4
established that the latter lacked the required `httpx` dependency. This is a
runtime repair, not an intervention; the executable identity is part of the
sealed launch path and has a deterministic regression test.

V5 advances only if C1 has at least two more R and F successes than C0 across
the 12 rows per condition, with no P or A decrease for either lower-conflict
sentinel. The pilot selects no release candidate. A separate unseen confirmation
bank and the fixed product regression panel remain mandatory before release.

The sealed bundle is `bundle.json` with SHA-256
`29f6f05ff6c410fa064c54fd0a356a2b5dd56298c9c7a60a456297e746ecd7a0`.
