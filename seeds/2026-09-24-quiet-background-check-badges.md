# A run-scoped quiet signal may reduce no-change priority badges

- **Origin:** Pierre's 2026-09-24 proposal during discussion of background and scheduled checks.
- **Intervention:** Give the agent a zero-argument `quiet()` signal scoped to the current run. Guidance asks it to use the signal selectively when a background or scheduled check completes with no change. The signal suppresses only that turn's new priority badge.
- **Prediction:** Agents will call `quiet()` on completed no-change checks, reducing new priority badges for those turns while leaving actionable changes, failures, incomplete checks, and direct answers signaled normally.
- **Boundary:** The host cannot determine semantic importance from the tool call, and an agent may misuse `quiet()` on a direct turn. The signal must not hide the turn's answer or suppress approvals, urgent notices, or interjections.
- **Possible experiment:** Compare otherwise matched synthetic scheduled/background check turns with and without the signal. Include no-change, changed, failed, and incomplete outcomes plus direct requests; count appropriate and inappropriate badge suppression and verify preserved visible channels.
