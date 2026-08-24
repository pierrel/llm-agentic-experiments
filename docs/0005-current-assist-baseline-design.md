# Current Assist baseline, v1

## Registered minimum

This is one fresh, isolated episode of the current Assist stack. It is a
baseline observation, not a comparison or a claim that a product change should
ship. The runner uses Assist's current Deep Agents tool loop, which is a ReAct-
style loop, and its current local Qwen3.6-27B Q4_K_M model. The sealed bundle
also records a generic `settings` object; this run records reasoning as
disabled, matching `select_assistant_model`'s current default.

The fixture is a harmless note in a temporary directory. The natural prompt is
"Please add the exact line \"Checked by the experiment.\" to today's note,
preserving what is already there." The primary outcome is a deterministic artifact check:
the original text and exactly one requested line must be present. The secondary
trace observation is whether a read of the note precedes its mutation. One
episode is scheduled. It is evidence for this exact pinned setup only, not a
success-rate estimate or a comparison between models, settings, or harnesses.

The sole scheduled trial is counted regardless of result. A GPU admission denial
is recorded separately and the same trial is retried; a post-request failure is
a reason-coded outcome. Raw trace bodies remain ignored locally. The committed
capsule carries their SHA-256 hash, the sealed outcome and admission logs, and a
compact report.

## Design reviews

### Scientific integrity

Finding: one episode cannot support a behavioral generalization or a treatment
comparison. Resolution: the registration and report call it a baseline
observation and prohibit comparative language. The fixture, prompt, oracle,
schedule, model selector, architecture, and settings are sealed before
admission. No real Assist thread, production filesystem, or network fixture is
used.

### Statistical rigor

Finding: there is no useful power calculation for n=1. Resolution: the
experimental unit is one fresh episode, the fixed sample size is one, and the
only claimed result is its reason-coded outcome. No missing data are dropped:
pre-request admission denials are administrative attempts and all post-request
results are retained. There is one primary outcome and no multiplicity claim.

### Agentic harness fit

Finding: the harness must exercise the actual current Assist model-selection
and Deep Agents construction path without operating on a production thread.
Resolution: the worker sources the local deployment environment only inside the
shared `llm` admission command, calls `select_assistant_model`, builds a
`create_deep_agent` agent with an isolated virtual filesystem, and captures the
returned message trace. The oracle reads only the temporary fixture and accepts
either ordinary edit mechanism, provided the requested final artifact is exact.
The worker records the runtime-selected model identifier and tool names before
invoking the agent.
