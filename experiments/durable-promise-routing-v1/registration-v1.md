# Durable-promise capability routing v1

Status: design registered. No model episode has run.

## Identity

- Study and version: Durable-promise capability routing v1.
- Lineage: `experiments/durable-promise-orchestration-v1/registration.md`,
  `results/2026-08-24-durable-promise-orchestration-v1/report.md`, and Assist
  eval commit `9a1e3149` are preserved exploratory inputs. They are not part of
  this cohort.
- Authors and pre-result reviewers: Pierre Larochelle; scientific-integrity,
  statistical-rigor, agentic-harness-fit, and minimum-adequate-setup reviews
  recorded in `design-review.md`.
- Date and model-run start: registered 2026-08-24; model-run start remains
  unset until the sealed adapter, bundle, and integrity tests are committed and
  locally reviewed.

## Question and hypothesis

Can a general grounding description distinguish a fact in the user's records
from a self-contained date or capability request, so the ordinary web main
grounds before a superficially matching generic capability while preserving the
existing completion lifecycle and honest durable response?

The control is the exact current Assist source. The sole treatment changes the
grounding skill description by adding this routing boundary:

> A question about the user's own date, time, meeting, deadline, or status
> needs this skill when the answer comes from their records.

The rest of that description and every other prompt, skill, tool, schema,
fixture, model setting, and runtime behavior remain identical. This is a
routing-only intervention: it neither changes the private-memory procedure nor
claims that all date language needs grounding.

## Minimum adequate setup

One unit is one fresh real-model ordinary-web-main agent run: fresh process,
thread, sandbox workspace, `/agent` directory, deterministic context-task
fixture, and no external network. The adapter must use current `create_agent`,
`prompt_rewrite_web_main_spec()`, `SandboxManager`, the same deterministic
async completion wake as the frozen EDD trajectory, and the production model
selection path. A scripted tool loop, raw chat completion, or shelling out to
pytest alone is inadequate because none captures the web-main skill catalog,
context-agent lifecycle, private state, or actual provider requests.

The adapter will capture every initial and subsequent rendered provider request,
complete dynamic tool schemas, tool calls/results, task-state transition,
message trace, final workspace digest, and final private-memory digest. It
will reject any source, fixture, schema, prompt, model, decoding, or settings
difference not declared in the sealed bundle. Raw traces remain private; the
result capsule stores their hashes and compact redacted evidence.

This study deliberately does not alter the active `time-skill-routing` lane's
unmerged `time` description. If that work lands before admission, this study is
superseded and re-registered against the new fixed baseline.

## Conditions and outcomes

Opaque conditions `C0` and `C1` are revealed only after the analysis artifact
is sealed. `C0` is current source; `C1` is the one description sentence above.
The causal primary is routing/lifecycle success (R): grounding is the first
loaded skill, the next action starts the context task, no user-file or unrelated
capability work precedes the trusted result, and that exact result is retrieved
before dependent work.

The product primary is full-row success (F = R and P and A):

- P: after the checked result, private `/agent/memory.md` records the requested
  future condition and response.
- A: the final answer uses the supplied local evidence and does not claim a
  write or completion that did not occur.

P conditional on R, answer quality, honesty, each predicate, and tool traces
are preregistered diagnostics. No qualitative judge is needed.

## Task split and sampling

The existing five dinner/calendar/budget compound rows are development and
regression diagnostics only. The earlier makerspace and internet-bill rows are
not confirmation holdouts because their results informed this registration.

Before any model run, the adapter will seal four new natural confirmation rows:
two local-record date/time or deadline requests with a separate future
commitment, and two lower-conflict local-fact-plus-commitment sentinels. Their
domains, files, facts, wording, and required terms must differ from the old
family. The fixed regression panel also includes direct time/date calculation,
recurring scheduling, inbound event subscription, grounding lifecycle, and the
existing durable-memory compaction behavior.

Development screening is N=3 per condition and task. A candidate that improves
R and F without a lifecycle or low-conflict P/A regression advances to a fixed
confirmation of N=14 per condition and each of the four locked rows (112
episodes). The confirmation schedule uses a registered seed and two-condition
blocks with an even replicate count, so each condition has each within-block
position equally often. Reuse one generation seed within a block only after a
sealed provider-seed calibration; otherwise episodes are independent and order
is the only blocked variable.

The committed development bundle is
`experiments/durable-promise-routing-v1/bundle.json` (SHA-256
`162ffa1b07caa65c5491456045a712f528311e2f3051944594d43928eda4b5a3`).
It schedules three fresh C0/C1 blocks for each of the four rows, 24 total
episodes, and pins the current source/model/harness settings. Its private
worker is `durable_routing_harness/`, deliberately isolated from the historical
MVP harness closure so adding this study cannot retroactively invalidate older
sealed evidence. The confirmation extension is a new bundle, not a rewrite of
this development schedule.

The registered schedule randomizes and counterbalances trial order. The local
OpenAI-compatible model's provider seed support has not been calibrated, so its
per-trial `generation_seed` values are identifiers for the fixed schedule only;
they are not sent as an unverified provider setting and do not create matched
pairs. This limitation is recorded before admission rather than inferred from
apparent repeatability.

There is no early success or futility stop in confirmation. Pre-request
production admission denials retry the same scheduled unit and are logged.
Post-request timeout, refusal, provider error, invalid trace, and loop
exhaustion are denominator failures with reason codes. A proven pre-request
harness fault may retry once, never silently.

## Analysis and release decision

The confirmation primary comparison reports pooled F and R risk differences
with two-sided 95% confidence intervals and per-task estimates. Secondary
p-values, if reported, use Holm correction and do not determine release.

A release candidate requires a worthwhile pooled improvement in F and R, a
nonnegative direction on every locked confirmation row, no P or A regression
on either low-conflict sentinel, and no repeated important failure on the fixed
regression panel. A smaller N=5/N=10 product stability panel can increase
operational confidence but is not presented as a powered statistical result.
Mixed or infeasible evidence rejects the treatment rather than rewriting a
confirmation row.

## Plain-language interpretation

If the treatment wins, it supports a narrow claim: making the local-record
boundary clearer in grounding's routing description helps this Qwen/Assist
combination choose grounding before generic date-like capability language. It
does not prove that repeated instructions are generally beneficial, that every
date request needs local context, or that durable commitments are solved across
all tasks.
