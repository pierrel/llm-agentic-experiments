# Sol should design and explicitly selected Terra agents should review

- **Origin:** Pierre's 2026-09-10 discussion of role ownership in the agentic
  development operation. He proposed that Sol own design while every design
  review lens is assigned to an explicitly selected Terra agent.
- **Intervention:** give Sol ownership of the feature design, including review
  orchestration and findings disposition. Sol assigns each required
  design-review lens to a separately selected Terra reviewer with the lens named
  in its task, then returns the consolidated plan to the coordinator for the
  implementation decision.
- **Prediction:** compared with the same lens assignments and sequencing using
  inherited or default model selection, explicit Sol authorship and Terra
  reviewers complete every required lens more consistently and surface more
  concrete design defects before implementation, while retaining traceable
  author-reviewer separation.
- **Boundary:** this role split does not make reviewer agreement evidence that a
  design is correct, and it must not erase a specialist requirement outside
  Terra's demonstrated capabilities. Trivial work that requires no design phase
  is outside the claim. An unavailable, failed, or timed-out Sol or Terra
  assignment must stop the phase or use a recorded fallback rather than silently
  changing the role or omitting a lens.
- **Possible experiment:** give matched synthetic feature briefs to the
  role-pinned workflow and an otherwise identical workflow using inherited or
  default model selection. Blindly score required-lens completion, verified
  pre-code findings, false positives, design churn during implementation, and
  author-reviewer provenance.
