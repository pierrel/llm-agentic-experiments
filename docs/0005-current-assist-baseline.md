# Current Assist baseline

This is the canonical narrative and chronological history for the first
current-Assist baseline. The immutable registrations under
`experiments/current-assist-baseline-v*/` and the v7 result capsule remain the
authoritative evidence; this document does not amend or replace them.

## Current profile

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

## Registered setup and result

The isolated fixture is a harmless note. The natural user prompt is:

> Please add the exact line "Checked by the experiment." to today's note,
> preserving what is already there.

The primary outcome requires the preserved initial text plus exactly one
requested line. The secondary observation is whether a note read precedes its
mutation. One fresh episode was scheduled, which is sufficient only to record
this exact outcome, not a success-rate, transfer, or treatment comparison.

The first registered real bundle, `current-assist-baseline-v7`, ran one
isolated episode. It sealed the fixture digest, natural prompt, current model
selection, ReAct-style architecture, generic settings including reasoning
disabled, and a recursion limit of 12. The capsule records the `Qwen3.6-27B`
family and `Q4_K_M` quantization; its model-weights digest was not captured.

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

## Design review and minimum setup audit

The original review concluded that one episode cannot support behavioral
generalization or a treatment comparison; the fixture, prompt, oracle,
schedule, model selector, architecture, and settings were fixed before
admission. No real Assist thread, production filesystem, or network fixture was
used. The experimental unit is one fresh episode, no post-request outcome is
dropped, and there is no multiplicity claim.

For harness fit, the worker selected Assist's model inside the shared `llm`
admission command, built an isolated `create_deep_agent` graph with the current
Assist construction, and recorded the selected model identity and tool names
before invocation. The oracle accepts either ordinary edit mechanism when the
final fixture is exact.

The required minimum-adequate-setup audit was missing before v7's model request.
Its post-run completion does not retroactively satisfy that gate. The isolated
note, natural edit request, current construction, and one bounded episode were
the minimum to observe that exact completion attempt, but not enough for a
success-rate, transfer, or product claim. Complete provider schemas, exact model
weights, and a clean Assist source tree were also not sealed; future real runs
must review and record those inputs before admission.

## Chronological history

The entries below replace the former standalone amendment and review documents.
They describe why each new sealed version existed; the corresponding bundle and
record files retain the authoritative original bytes.

### v1: initial registration, no model request

The admitted command could not import the experiment worker, and retry
bookkeeping assumed every attempt was number one. The ignored raw descriptor and
committed unsealed admission record remain pre-request operational evidence.

### v2: import path and retry accounting

V2 supplied the experiment package path to the admitted interpreter and derived
the next admission attempt from the append-only log. The task, fixture, prompt,
model, ReAct-style harness, reasoning setting, schedule, oracle, and analysis
revision were unchanged. It was denied while the shared LLM resource was busy,
before a model request.

### v3: admission bookkeeping and reasoning pass-through

V3 corrected the later-admitted retry number and explicitly passed the sealed
reasoning setting to Assist's model selector. No scientific input changed; the
original scientific, statistical, and harness reviews were rechecked.

### v4: pre-request measurement

V4 added snapshots of actual filesystem-tool schemas, rendered system-plus-user
messages, fixture digest, runtime model identity, and sealed settings before
`invoke`. It rejects a fixture or required-tool mismatch before a request. The
prompt, fixture, model selection, architecture, settings, oracle, and schedule
remained unchanged.

### v5: current Assist construction and accounting

V5 constructed the graph through `assist.agent.create_agent` with current Assist
middleware and an isolated virtual filesystem. A model callback captured every
pre-provider request; the runner bound itself to the registered tag, recorded
timeout/interruption as reason-coded outcomes, and required one exact requested
line. This was a measurement/accounting correction, not a treatment. It then
reported an infrastructure failure before a model request because the editable
Assist package could not find its templates.

### v6: Assist source identity

V6 added the current Assist source revision to the harness identity and placed
that source tree on `PYTHONPATH`, so `create_agent` used the templates and
middleware it claimed to baseline. It constructed the graph but the in-memory
checkpointer rejected invocation without a `thread_id`, before a model request.

### v7: experiment-scoped thread identity and historical pilot

V7 supplied a fresh deterministic experiment-scoped `thread_id`. The isolated
filesystem, Assist revision, model selection, reasoning setting, prompt,
fixture, oracle, and one-episode schedule were unchanged. It captured one
pre-provider request and then exhausted the 12-step recursion limit. That is the
reported historical-pilot outcome above.

## Post-run local review

The final review verified the v7 bundle, pre-provider capture hash, reason-coded
recursion-limit outcome, record seals, and report. The baseline-specific suite
then had 16 passing tests; the later integrated rebase check had 35, with
`compileall` and `git diff --check` clean.

Six real improvements are deliberately deferred because they would require a
new runner-hardening registration and, where applicable, a new real run:

1. Kill the whole admitted process group on parent timeout, so a timed-out
   worker cannot outlive the shared admission wrapper.
2. Replace the worker environment marker with wrapper-attested admission
   capability, so a local maintainer cannot invoke the worker directly.
3. Seal and compare complete provider tool schemas before request, so changed
   schemas cannot be mislabeled as the same setting.
4. Seal the resolved tag commit ID, not just the tag name, to strengthen
   historical anchoring against a moved tag.
5. Require a clean Assist source tree or seal its imported-tree digest, for
   exact harness reproducibility across workers.
6. Require the whole expected file for successful note-oracle evaluation, so a
   superficially correct requested line cannot conceal unrelated extra content.

After rebasing onto the scripted-MVP harness, the v7 executable runner could not
remain in top-level `harness/` without invalidating the MVP's sealed static
fixture. The final branch therefore retains the self-contained v7 result
capsule; its executable source is recoverable at
`a86178599a2d2ac2da76c24a645dcfa2ed47acbc`. The v7 episode itself is not
reproducible because model weights, complete provider schemas, and a clean Assist
source tree were not sealed. Do not rerun it from this integrated branch; create
a new registered study version instead.

## Record map

- `experiments/current-assist-baseline-v1/` through `v7/`: original sealed
  registrations and fixture bytes.
- `results/current-assist-baseline-v7/`: durable outcome, evidence inventory,
  learning, and Assist-roadmap proposal.
- `docs/study-registry.md`: compact version/status index.
