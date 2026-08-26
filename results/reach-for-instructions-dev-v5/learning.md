# V5 learning: one normalized status value can manufacture a cell contrast

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

V5 yielded a high-context 3/3 pass count for `G02` and 0/3 for `G01`, but two
`G01` traces contained all required grounded facts and ordered procedure with
the direct value `not_issued`. Because V5 accepted the equivalent
`no_payment_issued` but not `not_issued`, the contrast is an oracle artifact.
V6 isolates this final observed normalization before interpretation.

## Limits

V5 cannot establish a retrieved-versus-handed effect, a context threshold, or
transfer to a different task, model, architecture, or setting.

## Handoffs

No Assist action is proposed from this calibration result.
