# Current-Assist real-model coordinator design

Status: design review required. No model trial is authorized by this document.

## Question and minimum setup

The first run answers one operational question only: can the sealed experiment
path execute one fresh, hermetic task through the model and ReAct-style Deep
Agents loop that Assist actually uses, while preserving an auditable admission
and outcome record? It is not a prompt comparison and cannot establish a
product behavior claim.

The minimum adequate setup is therefore one registered fixture, one current
model identity, and one current Assist architecture profile. It retains the
real Deep Agents assembly because a raw OpenAI chat completion would change the
harness axis being established. It retains virtual fixture tools, one bounded
episode, complete request/response traces, and the deterministic artifact
oracle because those are necessary to establish fidelity and measurement. It
does not add a second model, an alternative architecture, a condition label,
network access, user data, a planner, subagents, or a larger task bank.

One episode is a smoke/pilot for the execution path, not a powered inference.
Any behavioral comparison requires a new Study A development registration and
its own sample plan.

## Immutable registration before admission

The coordinator will reject a real run unless a committed registration names:

- `Qwen_Qwen3.6-27B-Q4_K_M.gguf` and an operator-supplied weights SHA-256;
- `deepagents-langchain-tool-loop`, package versions, Assist source commit,
  exact selected graph profile, reasoning `{ "enabled": false }`, decoding,
  context limit, middleware/tool/subagent configuration, and loop bound inside
  generic sealed `settings`;
- the natural fixture prompt, virtual tool schemas, oracle, one scheduled
  trial, and a no-network/cache-disabled policy; and
- the immutable Git commit/tag which contains its content-addressed bundle.

The coordinator checks that immutable reference before recording an admission.
A changed model, architecture, test, or setting is a new bundle, never a retry.

## Execution boundary

`real_coordinator` owns the sealed output directory, schedule prefix, and
admission chain. For its current trial it invokes exactly one bounded worker
through `tools/agentic resource run llm -- ...`. The worker is not a public
"direct model" command: it receives only a sealed trial descriptor and returns
one result record. It imports the pinned Assist/Deep Agents profile, constructs
that profile against the hermetic virtual-tool adapter, and makes no network,
filesystem, shell, user-thread, or production-state capability available to the
agent.

The worker captures the assembled system/user messages, tool schemas, exact
provider request and reply payloads, tool events, package/source identities,
and timeout status. Before the provider request it compares those captures to
the bundle's declared invariants. Any mismatch is a reason-coded invalid
outcome and is not retried as a model sample. A refused resource admission is
an administrative admission record only and retries the same scheduled trial
later. A timeout or provider failure after request is a scored, reason-coded
episode outcome; it is never silently replayed.

## Required written reviews

Scientific integrity, statistical rigor, agentic-harness fit, and minimum
adequate setup must each review the concrete registration and worker contract.
The design record will list every verified finding, resolution, and declined
item before the coordinator is allowed to admit a model request. The existing
MVP integrity tests remain required, augmented by tests for Git binding,
refusal accounting, invariant capture, timeout classification, and absence of
a direct-model CLI path.

## Result handling

After a completed pilot, archive its capsule under `results/<run-id>/` before
interpretation. The capsule includes the sealed settings and registration
reference, admission/outcome chains, hashes of local raw traces, report, and
an explicit no-behavioral-learning limit. Only a later genuine learning creates
the linked private blog seed and an Assist-roadmap proposal.
