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

## Required first real-run profile

The first registered real bundle will use:

- the exact test fixture digest and natural user prompt from the test axis;
- model identity `Qwen_Qwen3.6-27B-Q4_K_M.gguf`, with the model-weights digest
  captured before admission;
- architecture identity `deepagents-langchain-tool-loop`, with the pinned
  package versions and Assist graph configuration; and
- one generic `settings` object. At minimum it records the OpenAI-compatible
  provider shape, reasoning `{ "enabled": false }`, decoding, context limit,
  tool/middleware/subagent configuration, loop bounds, and cache policy.

No real model trial has run. The endpoint's model ID is not a substitute for a
weights digest, so the coordinator must fail closed until that digest is
provided. A future model or plan-and-execute comparison keeps the test digest
unchanged, changes exactly one declared axis, and writes a new sealed bundle.
