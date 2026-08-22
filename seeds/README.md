# Hypothesis seeds

Use one short Markdown file per claim, named `YYYY-MM-DD-slug.md`. A seed is a
durable research lead taken from a product conversation, review, or observed
trace. It is deliberately weaker than a study registration: do not report a
result or tune a product from a seed alone.

```md
# Concise claim

- **Origin:** conversation, review, or trace reference.
- **Intervention:** the prompt or mechanism change being proposed.
- **Prediction:** observable agent behavior expected to change.
- **Boundary:** a plausible counterexample, adjacent workflow, or condition
  that must remain unaffected.
- **Possible experiment:** a short controlled comparison, if known.
```

Promote a seed only by writing a committed registration under
`experiments/<study>/`; preserve the seed as the original rationale.
