# Pre-admission event

On 2026-08-24, the first scheduled v2 development worker stopped in runtime
validation before the shared-GPU worker process was constructed or a provider
request was made. The sealed architecture setting stored abbreviated Assist
revision `41c8b146`; the validator correctly compares the full merge-base SHA
and rejected it as an ambiguous baseline identity.

Raw private output directory: `results/raw/durable-orchestration-v2.nJyVTb`.
It contains no model trace, admission record, or outcome. The v2 bundle and tag
remain immutable evidence of this invalid preflight. V3 repeats the same
development question with the full Assist commit identity and a new sealed
bundle; it is the first model-capable version.
