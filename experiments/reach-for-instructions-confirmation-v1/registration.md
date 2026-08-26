# Reach-for-instructions held-out confirmation registration v1

## Question

On a task that was not used to design the development screen, does allowing the
agent to retrieve a matching procedure produce a higher complete
procedure-plus-artifact success rate than handing the same procedure to the
agent in its system context?

## Fixed plan

- **Experimental unit:** one fresh agent episode in a new private filesystem.
- **Task:** the new Cedar Loop access-transition handoff fixture. It shares no
  reimbursement case, record text, identifiers, expected facts, or output
  domain with V7. Its natural request names no skill, tool, path, source file,
  or oracle phrase.
- **Conditions:** opaque `G01` receives the complete access-transition
  procedure in system context before its first decision. Opaque `G02` receives
  the same catalog and tool but must request the same procedure through
  `load_skill`. No capability is removed from `G01`.
- **Context doses:** 0, 900, and 3,600 inert filler lines. The procedure,
  catalog, task, fixture, tools, decoding, model, reasoning setting, and
  harness are otherwise matched within every dose.
- **Sample and randomization:** 12 fresh episodes per delivery-by-dose cell,
  72 total. The schedule is deterministically interleaved by paired condition
  block using randomization seed `20260826`; no post-result stopping or
  replacement is allowed. This yields 36 episodes per delivery condition. It
  is powered as an aggregate transfer confirmation screen, not as a precise
  estimate in each 12-episode dose cell.
- **Runtime:** Qwen3.6-27B Q4 through the pinned current Assist Deep Agents
  tool loop, reasoning disabled, temperature 0.1, 1,200 output tokens,
  recursion limit 20, a private virtual filesystem, default Deep Agents
  filesystem/TODO/task tools, and one fixed `load_skill` tool. There are no
  caller tools or subagents.
- **Primary outcome:** a condition-blind deterministic oracle requires exactly
  one grounded JSON handoff, immutable source records, inventory and every
  source read before writing. The sealed preflight accepts two independently
  grounded output forms and rejects one unsupported account. Every admitted
  terminal episode is retained with its reason code; a denied shared-resource
  admission retries the same scheduled episode before the schedule advances.
- **Analysis:** report reason-coded outcomes, complete-pass counts by delivery
  and context dose, the aggregate delivery contrast over 36 episodes per arm,
  first provider-request token counts, and whether the skill loaded before the
  first source read. The confirmation claim is limited to a directionally
  consistent aggregate advantage for `G02` on this held-out task; it makes no
  context threshold or Assist product claim. Any model, harness, reasoning, or
  task transfer is separately untested.

## Design review record

Scientific integrity, statistical rigor, agentic-harness fit, and minimum
adequate setup reviews are recorded in
`docs/0026-reach-for-instructions-confirmation-v1-design-review.md` before
model admission. The bundle, per-trial post-middleware provider-request digests,
fixture, conditions, preflight, schedule, runtime settings, implementation, and
analysis plan are tagged before the cohort begins.
