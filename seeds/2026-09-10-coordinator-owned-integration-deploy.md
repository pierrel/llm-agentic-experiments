# A durable coordinator should integrate compatible lane changes before deployment

- **Origin:** Pierre's 2026-09-10 discussion of changes to the agentic
  development operation. He proposed that the durable coordinator should, by
  default, deploy same-repository work together when overlap is minimal,
  potentially through a coordinator-owned merge worktree.
- **Intervention:** give the durable coordinator an integration worktree where
  it combines pinned commits from independently reviewed same-repository lanes
  that are ready at the same time and have minimal actual coupling. Preserve
  each commit's provenance, verify one immutable integration revision, and
  deploy it once through the existing shared transaction.
- **Prediction:** compared with deploying each compatible lane separately, the
  coordinator produces fewer deployment transitions while still identifying
  which lane supplied every change, without increasing time from lane readiness
  to deployment or integration failures.
- **Boundary:** do not delay ready work to await a possible batch. Fix batch
  membership when combined verification starts and defer later arrivals. Any
  actual shared code, contract, runtime resource, migration, deployment state,
  or active user-testing dependency is meaningful overlap, even when files are
  disjoint. No lane or combined revision advances without its required checks;
  a failed batch may be split for diagnosis, but every resulting revision must
  pass before deployment. Confirmed coupling requires changed work or an
  explicitly reviewed dependency order.
- **Possible experiment:** replay synthetic sets of simultaneously ready lanes
  with known compatible and conflicting changes. Hold the review, provenance,
  and deployment safeguards constant; compare separate deployment with the
  coordinator-owned integration policy on deployment count, readiness-to-live
  latency, provenance recovery, conflict detection, integration failures, and
  incorrect bundling.
