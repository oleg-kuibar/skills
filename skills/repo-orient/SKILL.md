---
name: repo-orient
description: "Orient to an unfamiliar software repository before coding, reviewing, or debugging. Use when an agent needs to inspect project structure, identify frameworks and test commands, find likely ownership boundaries, and report an evidence-backed starting point for developer work."
---

# Repo Orient

## Workflow

1. Identify the repo's primary languages, package managers, frameworks, runtime
   entry points, and test commands from available files.
2. Trace the requested work to likely files or modules. Prefer evidence from
   imports, route definitions, package scripts, tests, config files, and naming
   conventions.
3. Separate known facts from likely inferences. Mark inferences clearly.
4. Report the smallest useful orientation:
   - `Stack`
   - `Entry Points`
   - `Relevant Files`
   - `Tests And Checks`
   - `Risks Or Unknowns`
   - `Suggested First Move`
5. Do not propose broad rewrites unless the evidence shows the current shape is
   blocking the work.
6. If file contents are missing, name exactly which files would most reduce
   uncertainty.
