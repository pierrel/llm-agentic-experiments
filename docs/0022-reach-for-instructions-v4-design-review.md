# Reach-for-instructions v4 design re-review

V3's first admitted worker never reached a model callback because the shared
admission wrapper executed it from another working directory and its descriptor
path was relative. V4 changes only descriptor, result, and marker arguments to
absolute paths and adds a no-model contract test.

- **Scientific integrity:** the V3 admission record shows no request marker;
  no result informed V4. The prior bundle is retained unchanged.
- **Statistical rigor:** no scheduled cell, replicate, randomization, or score
  changed.
- **Agentic harness fit:** absolute private-artifact paths make the worker
  independent of the coordinator's working directory while preserving the same
  admission boundary.
- **Minimum adequate setup:** no new harness capability or experimental factor
  was added.
