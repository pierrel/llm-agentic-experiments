# Reach-for-instructions confirmation V7: partial non-diagnostic execution

V7 r5 is a sealed 72-episode registration. Its execution stopped after 13
terminal episodes rather than broaden the oracle after observing its first new
representation boundary. All 13 made provider requests and were recorded; none
are interpreted as a delivery effect.

The raw private chain contains 14 admission records and 13 outcomes: G01 7,
G02 6; C-low 6, C-medium 4, C-high 3. Its evidence digests are:

```text
admissions.jsonl  fef6af9535e61df2ab67a6f94abe47196e2d06165b0fd45e156767261cae79c1
outcomes.jsonl    afdcce2443c490944039a1e124cef99d21bc2919a5e24d96bc3303bafbb79920
traces aggregate  0486293d50d3f55d25da7db7576a96d4adaabbabc7a45a134ad76ee3a401d997
```

Trace inspection shows grounded handoffs consistently use the compact approval
value `conditionally_approved_pending_intake_photo`. It preserves conditional
approval and the pending-photo constraint, but omits Supervisor Maren because
the requested output has an approval-status field, not a supervisor field. V7's
preregistered oracle required `maren` in that field and therefore rejects this
source-supported form. Retrofitting V7 is not valid. A new fixture and fresh
pre-admission calibration are required before resuming the hypothesis test.
