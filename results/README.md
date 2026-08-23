# Result capsules

Every completed experiment run receives a new committed directory:

```text
results/<run-id>/
  bundle.json                 sealed setting, schedule, fixtures, model, architecture
  admissions.jsonl[.seal]     admission history
  outcomes.jsonl[.seal]       scored results and the final evidence seal
  report.json                 aggregate result summary
  run.json                    capsule inventory and raw-trace hashes
  learning.md                 observation, evidence, limits, and counterexamples
  assist-roadmap-proposal.md  proposed product follow-through, if warranted
```

Use `harness.archive_scripted_run` after a finalized scripted run. The archive
verifies the source final seal before copying commit-safe artifacts. Raw trace
bodies remain under ignored `results/raw/` by default, but `run.json` retains
the exact trace hashes bound by the final seal.

The synthetic MVP capsule contains no behavioral learning. It proves only that
the measurement and history path works. When a real result warrants a learning,
write it in `learning.md`, create one private `larochelle.io/seeds/` seed with
the capsule as evidence context, and fill in the Assist-roadmap proposal. Do
not treat that handoff as approval to change Assist.
