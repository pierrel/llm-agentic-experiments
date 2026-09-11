# Reach-for-instructions confirmation V6: partial non-diagnostic execution

V6 is a sealed 72-episode registration, but its execution stopped after 13
terminal episodes and must not be analyzed as a guidance result. All 13 made a
provider request and were scored `artifact_failure` with the same reason:
`handoff has an unsupported or incomplete fact`.

The retained raw evidence is local and private because it contains full model
traces. At pause time it had 20 admission records and 13 terminal outcome
records. The outcome condition count was G01 6, G02 7; the context count was
C-low 6, C-medium 2, C-high 5. The raw chain digests are:

```text
admissions.jsonl  ebdd6c9076aa776db24ccf6a5a29db64a2dedd2b0eacbe762ff17a7e0c663116
outcomes.jsonl    b473deebd077606fc803f2b8c8b203c69ed40da0f05f65f825db0115a55661c6
traces aggregate  7fe051eccb3c23ca95b94f894e77a589d423fa127bd984ce3cb1a056bc2a7889
```

Inspection of the retained handoffs found the source-supported compact
`return_status: not_completed` paired with conditional approval in another
field. V6's preregistered oracle required the word `approved` in the status
field itself. Changing that oracle after its first model request would be an
unregistered amendment, so V6 remains immutable. V7 is the fresh held-out
study that tests the corrected boundary.
