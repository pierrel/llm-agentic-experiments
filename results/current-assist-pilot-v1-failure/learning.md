# Execution finding: worker import path was relative to the wrapper cwd

## Evidence

- Sealed run: `run.json` (bundle `43e1b48479fe85b4ff047915899500865fa954cc0dab830d28a918569846d810`)
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

The first attempt was denied because production held the GPU. The second was
admitted but failed before importing `harness.current_worker`: the coordinator
passed `PYTHONPATH=.` and the shared admission wrapper ran from the workspace
root, not the experiment checkout. The sealed raw trace contains only this
`ModuleNotFoundError`; it contains no model response or tool call.

The v1 outcome record marks `model_request_made=true` because it equated a
successful admission-wrapper command with a model request. That field is not
evidence of a request for this run. The trace and worker error are the primary
evidence that no model episode occurred.

## Limits

This is an execution-infrastructure finding, not evidence about model behavior,
the test, the Deep Agents architecture, reasoning, or Assist guidance. A new
registered version must use an absolute experiment-root import path and record
pre-worker startup failures without claiming a model request.

## Handoffs

It is not a behavioral learning and does not warrant a blog seed or Assist
product change. It does require a lab-runner correction before the next pilot.
