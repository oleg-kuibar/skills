---
name: focused-code-edit
description: "Make small, scoped code edits from selected code or a narrow file snippet. Use when an agent needs to preserve behavior outside the requested change, avoid speculative refactors, and return a minimal patch or replacement for day-to-day developer edits."
---

# Focused Code Edit

## Workflow

1. Identify the exact requested behavior change and the selected code scope.
2. Preserve existing public behavior outside that scope.
3. Prefer the smallest readable edit over a broad refactor.
4. Keep names, style, and control flow consistent with the surrounding snippet.
5. Note any important assumption if the snippet lacks types, tests, or call-site
   context.
6. Return a patch or replacement snippet first. Add explanation only when it
   helps the developer review the change.
7. Do not claim tests passed unless a relevant test command actually ran.
