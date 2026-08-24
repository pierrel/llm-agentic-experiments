# Current Assist baseline v5 amendment

V5 resolves the local review findings before any model request. The isolated
worker now constructs the agent through `assist.agent.create_agent` with the
current Assist middleware and an isolated virtual filesystem. A callback on the
selected Assist model stores every actual provider request, including later
ReAct turns, before the provider call. The runner rejects a bundle or runner
source that differs from the registered tag, records timeout or interrupted
admitted workers as reason-coded outcomes, and requires the requested text to
be one exact line.

These are measurement and accounting corrections, not experimental treatments.
The fixture, natural prompt, current-model selector, reasoning value, one-episode
schedule, and primary question are unchanged. The three original design-review
lenses were rechecked for this exact Assist construction and remain valid.
