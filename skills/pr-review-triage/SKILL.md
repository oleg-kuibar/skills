---
name: pr-review-triage
description: "Review software diffs for bugs, behavioral regressions, missing tests, and risky assumptions. Use when an agent needs to produce code-review findings grounded in changed lines and prioritize issues over summaries."
---

# PR Review Triage

## Workflow

1. Read the stated intent, then inspect the diff for changed contracts, control
   flow, data shapes, persistence, authorization, concurrency, error handling,
   and tests.
2. Lead with actionable findings. Omit style preferences unless they create a
   real maintenance or behavior risk.
3. For each finding, include:
   - severity: `P0`, `P1`, `P2`, or `P3`
   - changed file and line or hunk reference
   - observed behavior from the diff
   - why it is a bug, regression, or test gap
   - a concise fix direction
4. Prefer fewer, stronger findings over a long list of speculative concerns.
5. If no issue is found, say so and name any residual risk from missing context
   or unrun tests.
6. Do not approve or reject the PR unless the user explicitly asks for that
   decision.
