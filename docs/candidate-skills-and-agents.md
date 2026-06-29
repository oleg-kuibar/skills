# Candidate Skills and Agents

Research date: 2026-06-21.

This is the intake list for useful daily-development skills and agents that are
not installed in this repo yet, plus a record of candidates promoted into the
installable library. Keep this file separate from `skills/` and `agents/`:
candidates should become installable only after they look useful in real work,
not just because the upstream README is appealing.

## Selection Bar

A candidate belongs here when it helps with one of these repeated developer
jobs:

- shipping PRs and watching CI
- reviewing, verifying, testing, and debugging code
- browser/UI inspection with real runtime evidence
- maintaining useful project memory and status updates
- designing interfaces or docs that come up in normal product work

Prefer sources that are real `SKILL.md` or agent files, maintained in public
repos, and easy to pin by commit SHA in `sources.json`.

## Already Covered

The current library already has strong coverage for:

- React and composition guidance from Vercel:
  `vercel-react-best-practices`, `vercel-composition-patterns`
- strict review, verification, weekly review, and merge conflicts from Cursor:
  `thermo-nuclear-code-quality-review`, `verify-this`, `weekly-review`,
  `fix-merge-conflicts`
- PR and CI shipping loops from Cursor:
  `fix-ci`, `loop-on-ci`, `get-pr-comments`, `make-pr-easy-to-review`, and the
  `ci-watcher` agent
- docs interrogation and domain modeling from Matt Pocock:
  `grill-with-docs`, `domain-modeling`

Do not add near-duplicates unless they give a clearly different workflow.

## Promoted on 2026-06-21

These candidates were promoted from the research list into `sources.json` and
vendored as real installable files:

| Candidate | Type | Why it was promoted |
| --- | --- | --- |
| `fix-ci` | skill | Turns failing PR checks into a concrete diagnose/fix/recheck loop. |
| `loop-on-ci` | skill | Watches PR checks with `gh pr checks` and repeats until green. |
| `ci-watcher` | agent | Background CI monitor; pairs naturally with `fix-ci` and `loop-on-ci`. |
| `get-pr-comments` | skill | Converts PR feedback into an actionable summary. |
| `make-pr-easy-to-review` | skill | Improves reviewer experience without changing behavior. |

## Best Next Additions

These are the highest-fit candidates because they are small, daily-useful, and
come from upstreams already aligned with this repo.

| Candidate | Type | Source | Why it fits |
| --- | --- | --- | --- |
| `review-and-ship` | skill | [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/review-and-ship) | Good umbrella for final local review, tests, commit, and PR update. |
| `check-compiler-errors` | skill | [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/check-compiler-errors) | Narrow, useful loop for type-check and compile failures. |
| `run-smoke-tests` | skill | [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/run-smoke-tests) | Playwright smoke-test workflow with debugging and rerun discipline. |
| `what-did-i-get-done` | skill | [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/what-did-i-get-done) | Converts authored commits into a concise status update for a real date range. |
| `workflow-from-chats` | skill | [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/workflow-from-chats) | Mines durable personal/team workflow preferences into future skills or docs. |
| `find-skills` | skill | [vercel-labs/skills](https://github.com/vercel-labs/skills/tree/main/skills/find-skills) | Meta-skill for discovering installable skills when a task needs specialized help. |

Recommended next batch: add `check-compiler-errors`, `run-smoke-tests`, and
`what-did-i-get-done` if the promoted PR/CI cluster proves useful in actual
shipping work.

## Strong Skill Candidates

These are useful but should be adopted selectively, not as a whole pack.

| Candidate | Type | Source | Notes |
| --- | --- | --- | --- |
| `source-driven-development` | skill | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/source-driven-development) | Good for modern framework work where official docs matter more than memory. |
| `debugging-and-error-recovery` | skill | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/debugging-and-error-recovery) | Root-cause debugging loop; overlaps somewhat with existing verification, but broader. |
| `incremental-implementation` | skill | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/incremental-implementation) | Good discipline for multi-file work; could become noisy if it over-triggers. |
| `browser-testing-with-devtools` | skill | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/browser-testing-with-devtools) | Excellent for browser runtime evidence when Chrome DevTools MCP is available. |
| `webapp-testing` | skill | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/webapp-testing) | Strong Playwright workflow; includes helper scripts, but check licensing before vendoring. |
| `mcp-builder` | skill | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) | Useful only if MCP server creation becomes recurring work. |
| `decisions` | skill | [maragudk/skills](https://github.com/maragudk/skills/tree/main/decisions) | Lightweight decision log; complements `domain-modeling`. |
| `design-doc` | skill | [maragudk/skills](https://github.com/maragudk/skills/tree/main/design-doc) | Short spec/design-doc habit after brainstorms. |
| `address-code-review` | skill | [maragudk/skills](https://github.com/maragudk/skills/tree/main/address-code-review) | More interactive than Cursor's PR-comment summary; use if you want one-comment-at-a-time review handling. |
| `worktrees` | skill | [maragudk/skills](https://github.com/maragudk/skills/tree/main/worktrees) | Useful if parallel agent worktrees become part of your normal workflow. |
| `webapp-testing` | skill | [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/webapp-testing) | Simpler than Anthropic's version; good if you want a lightweight Playwright skill. |
| `web-design-reviewer` | skill | [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/web-design-reviewer) | Useful for visual QA, but may need editing to match this repo's design standards. |
| `ui-screenshots` | skill | [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/ui-screenshots) | Practical before/after screenshot workflow for UI changes. |

## Agent Candidates

Prefer agents that are narrow enough to delegate to and easy to validate.

| Candidate | Source | Fit | Vendoring notes |
| --- | --- | --- | --- |
| `code-reviewer` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/blob/main/agents/code-reviewer.md) | Solid general review persona; overlaps with thermo-nuclear review but less severe. | Easy to vendor as a real file. |
| `test-engineer` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/blob/main/agents/test-engineer.md) | Useful for test planning and coverage gaps. | Easy to vendor as a real file. |
| `security-auditor` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/blob/main/agents/security-auditor.md) | Good focused security pass, including AI/LLM feature risks. | Easy to vendor as a real file. |
| `web-performance-auditor` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/blob/main/agents/web-performance-auditor.md) | Strong if frontend performance audits happen often. | Easy to vendor as a real file. |
| `DevTools Regression Investigator` | [github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/agents/devtools-regression-investigator.agent.md) | Good browser-evidence specialist for regressions. | Needs normalization: upstream `name` uses spaces and the file is `.agent.md`. |
| `Frontend Performance Investigator` | [github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/agents/frontend-performance-investigator.agent.md) | Runtime CWV/performance investigation. | Needs normalization before this repo's checks will pass. |
| `Accessibility Runtime Tester` | [github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/agents/accessibility-runtime-tester.agent.md) | Strong for keyboard/focus/runtime a11y testing. | Needs normalization before this repo's checks will pass. |
| `GitHub Actions Expert` | [github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/agents/github-actions-expert.agent.md) | Useful when workflow security and supply-chain hardening are frequent. | Needs normalization and may be stricter than this repo currently is. |

## Hold or Skip

- Do not vendor whole marketplaces like
  [wshobson/agents](https://github.com/wshobson/agents). It is useful as an
  external marketplace, but too broad for a personal `skills.sh` repo without a
  specific plugin choice.
- Avoid bulk skill packs that look generated or unfocused. A huge count is not a
  quality signal.
- Treat highly version-specific personas, such as React or Next.js agents pinned
  to a future/current minor, as project-specific. They can go stale faster than
  skills that say "detect the version, then use official docs."
- Do not add `skills-directory/skill-codex` unless you regularly drive Codex
  from another agent host. It is useful in that host, not inside Codex itself.
- Do not vendor Anthropic source-available document skills unless the license
  and intended use are explicitly acceptable.

## Adoption Workflow

1. Use a candidate manually in real work at least twice.
2. If it is still useful, add it to `sources.json` with a pinned commit SHA and
   `track`.
3. Run `python3 tools/sync_sources.py` to vendor real files.
4. Update `skills.sh.json`, README credits, and this file.
5. Run `python3 tools/sync_sources.py --check`.
6. Let the daily update workflow keep the pinned upstream current through PRs.

For Awesome Copilot agents, add a normalization step before vendoring or create
local wrapper agent files. This repo's check expects `agents/<name>.md` and a
frontmatter `name` matching the file stem.

## Research Sources

Local snapshots inspected:

- `addyosmani/agent-skills` at
  `17214a29c429a19f7a9607f2c06f9d650ea87eb0`
- `cursor/plugins` at
  `e46364b8be46000b7df0f260550cd712afbb8d36`
- `github/awesome-copilot` at
  `251f416b6d3aa12837b10536e6f9bdd67f482ff7`
- `anthropics/skills` at
  `57546260929473d4e0d1c1bb75297be2fdfa1949`
- `maragudk/skills` at
  `9859f7bceb7a46af8482cabb9aa24e0d38a49413`
- `vercel-labs/skills` at
  `e5c075e3a84b37c5eb398ab74e581558d3fceb0e`
- `wshobson/agents` at
  `cc37bfdd292ce520ba1c44df7a3a70d5f8137236`
- `skills-directory/skill-codex` at
  `0cce7fc7c49b08fd60ae05bdf7934590d7bc34b5`

External docs checked:

- [GitHub Docs: About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [GitHub Changelog: Manage agent skills with GitHub CLI](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/)
- [Awesome Copilot skills directory](https://awesome-copilot.github.com/skills/)
- [Anthropic public skills repository](https://github.com/anthropics/skills)
- [Vercel `find-skills` skill](https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md)
