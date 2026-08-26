# Reach-for-instructions v3 design re-review

V2 received no model request. The runner created a fresh raw-output directory
at mode 0755, then rejected it under its own privacy guard before running the
worker. V3 changes only that creation mode to 0700 and receives a new ID,
bundle, commit, and tag.

- **Scientific integrity:** V1 and V2 remain tagged, unexecuted records; no
  outcome informed V3.
- **Statistical rigor:** no task, condition, dose, replicate, schedule, or
  scoring change occurred.
- **Agentic harness fit:** the same gated worker starts only after the raw
  trace destination is private.
- **Minimum adequate setup:** this is the smallest correction that makes the
  registered private-trace containment reachable.
