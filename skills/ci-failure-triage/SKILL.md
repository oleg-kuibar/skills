---
name: ci-failure-triage
description: "Diagnose failing CI, test, lint, build, or typecheck output from logs and repository context. Use when an agent needs to identify the likely failing layer, distinguish root cause from cascading noise, propose the smallest fix, and name verification commands."
---

# CI Failure Triage

## Workflow

1. Read the failure log from the first actual error upward and outward. Ignore
   later failures until the earliest plausible root cause is understood.
2. Classify the failing layer: install, build, lint, typecheck, unit test,
   integration test, e2e test, deploy, or environment.
3. Extract concrete evidence:
   - failing command
   - failing file, line, or test name
   - exact assertion or error message
   - recent changed surface if available
4. Distinguish root cause, likely contributing factors, and unrelated noise.
5. Propose the smallest safe fix. If multiple fixes are possible, rank them by
   evidence and blast radius.
6. Name the verification command that should prove the fix.
7. Avoid claiming the fix is confirmed unless the relevant command has actually
   run and passed.
