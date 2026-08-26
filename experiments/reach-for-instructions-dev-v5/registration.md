# Reach-for-instructions development registration v5

V4 completed all 18 admitted episodes. Its handoffs consistently contained the
requested grounded facts but used the natural field names
`verified_amount_cents` and, in some episodes, `remaining_uncertainty`; payment
status also used direct normalized forms such as `not_paid` and
`no_payment_issued`. V4's fixed key names therefore scored every completed
handoff as failure, masking any guidance-delivery contrast.

V5 changes only the fixture/oracle declaration before new model requests. It
accepts either declared amount key and either declared uncertainty key, and
retains the existing direct non-issued-payment forms. It still requires the
same case, amount, receipt, owner, action, source immutability, inventory, all
source reads before writing, and one JSON output. The question, opaque delivery
conditions, user request, three inert context doses, 18-episode interleaved
schedule, model, reasoning setting, architecture, decoding, tools, and skill
body are unchanged.

This is the first result-informed development variant. It remains exploratory:
all outcomes are retained and it cannot establish transfer beyond the pinned
current-Assist model and Deep Agents loop.
