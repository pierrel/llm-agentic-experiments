# Pre-admission events

This immutable event log preserves operational facts that are not model-result
evidence. It does not alter the registered tasks, conditions, or outcome rules.

## 2026-08-24: first C0 launch failed before a model request

The first scheduled C0 `library-shift` worker was admitted by the shared GPU
wrapper but exited during its sealed setup. Its lifecycle record remained
`launch-intent`; the outcome chain records `infrastructure_invalid` with
`model_request_made: false`. No provider request, tool call, or agent response
was produced, so this is not a baseline observation and cannot be replayed
inside the sealed v1 schedule.

The private raw directory is `results/raw/durable-routing-v1.ZzduO9` (mode
0700). Its retained artifact hashes are:

- bundle: `01df186650bf37ae23bc18557199cad2007ae09e3f704b6b5eff86eb195ebcfb`
- admission chain: `0b15aecf5458a56b142f700240ff9a134f972fafc969859ea414a195b56f7919`
- outcome chain: `de6cec9994e85eb1d2aa09e1f2e0f31bd4c76478d0673e2ceaa2b6bb4aa1f4c0`
- private trace: `42072b3b0443a5d6e6b2b8c95dee28af918b3242c49a5474be4971106fcc9b12`

The immediate standalone preflight subsequently validated the exact served
model identity and context and reached the `worker-started` lifecycle state
without calling the graph. The cause therefore remains unknown rather than
being attributed to the model or prompt. A later study version must be
registered instead of replacing this event.
