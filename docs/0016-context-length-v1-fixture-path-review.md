# Context-length v1 fixture-path revision review

Date: 2026-08-25. Runtime-source revision `r2` made no model request: its
fixture preflight rejected normal relative paths because it inspected the joined
temporary-root path. This revision moves the check to the unjoined input and
adds direct coverage for accepted relative and rejected absolute/traversal
paths.

No treatment, fixture content, model setting, harness shape, schedule, or
oracle changes. The revision is required to make the previously sealed minimum
task executable, not to move a flat behavioral result.
