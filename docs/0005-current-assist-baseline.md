# Current Assist baseline profile

## Confirmed baseline

The first real-model experiment profile targets the architecture Assist runs
today, rather than a hypothetical planner. Assist calls Deep Agents
`create_deep_agent` in `assist/agent.py`; Deep Agents 0.6.1 assembles its
middleware, tools, filesystem/backend, skills, and configured subagents, then
delegates the model/tool graph to LangChain `create_agent`. LangGraph executes
that graph. This is a model-decides / tool-runs / tool-result-returns loop with
todo planning available inside the loop: reasonably called ReAct-style, but not
a separate plan-and-execute controller.

The installed Assist lock pins Deep Agents 0.6.1, LangChain 1.3.1, and LangGraph
1.2.0. Assist's production model selector probes its OpenAI-compatible endpoint
and currently observed `Qwen_Qwen3.6-27B-Q4_K_M.gguf` on 2026-08-23. The
production wrapper `select_assistant_model` sets Qwen reasoning off unless a
caller deliberately overrides it.

Deep Agents documents the same construction: `create_deep_agent` composes the
agent harness and calls LangChain's `create_agent`; LangGraph drives the model
and tool loop. Its built-in todo capability is planning support, not evidence
of a plan-and-execute architecture. See the [Deep Agents architecture
document](https://github.com/langchain-ai/deepagents/blob/main/libs/ARCHITECTURE.md)
and [customization guide](https://docs.langchain.com/oss/python/deepagents/customization).

## First real-run record

The first registered real bundle, `current-assist-baseline-v7`, ran one
isolated episode. It sealed the fixture digest, natural prompt, current model
selection, ReAct-style architecture, generic settings including reasoning
disabled, and a recursion limit of 12. The runtime reported
`Qwen_Qwen3.6-27B-Q4_K_M.gguf`; its model-weights digest was not captured.

The episode captured one pre-provider request and then exhausted the sealed
recursion limit before returning the requested edit. Its sealed record keeps the original
`provider_error` reason code and exact `GraphRecursionError` detail. The capsule
adds the non-mutating observation that this was loop exhaustion, not a provider
availability failure. See `results/current-assist-baseline-v7/`.

The required minimum-adequate-setup audit was completed only after the run, so
v7 is a historical pilot rather than a compliant confirmation.

The missing weights digest is a limitation of this historical run, not a reason
to rewrite it. A future model or plan-and-execute comparison must keep the test
digest unchanged, change exactly one declared axis, and write a new sealed
bundle with its own model identity and settings.
