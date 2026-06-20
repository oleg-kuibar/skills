# Skills Repo Patterns

This lookup is a grounding note for keeping this repository close to real
developer skill practice rather than drifting into a prompt scrapbook.

## What Modern Skill Repos Share

Real agent skill systems converge on the same package shape:

```text
skill-name/
  SKILL.md
  scripts/
  references/
  assets/
  agents/
```

`SKILL.md` is the activation and workflow entry point. Larger examples, helper
programs, documents, and assets live beside it so agents can load them only when
needed.

Sources:

- OpenAI Codex skills: https://developers.openai.com/codex/skills
- Claude Code skills: https://code.claude.com/docs/en/skills
- GitHub Copilot agent skills: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills
- Anthropic public skills repo: https://github.com/anthropics/skills
- Vercel Labs skills tool: https://github.com/vercel-labs/skills

## Discovery Locations Matter

The common discovery locations are platform-native folders, not arbitrary docs
folders:

- Codex: `.agents/skills`, user-level `.agents/skills`, admin/system locations.
- Claude Code: `.claude/skills`, `~/.claude/skills`, plugin skill folders.
- GitHub Copilot: `.github/skills`, `.claude/skills`, `.agents/skills`,
  personal `~/.copilot/skills`, and personal `~/.agents/skills`.

For this repo, `skills/` should remain the canonical source of truth, but harness
adapters should project those same skills into platform-native locations when a
run needs them.

## Description Is Routing

Skill descriptions are not decorative metadata. They are the routing layer for
implicit activation, and they get compacted first in large skill sets.

Good descriptions should:

- Start with the task trigger.
- Say when to use the skill.
- Avoid broad claims like "helps with coding."
- Keep boundaries explicit enough that unrelated tasks do not activate it.

## Skills Are Not Always-On Instructions

Always-relevant repo rules belong in repo instruction files such as `AGENTS.md`,
custom instructions, or equivalent harness config. Skills are for detailed,
task-specific workflows that should be loaded only when relevant.

That keeps daily agent context smaller and makes skill selection measurable.

## Security Is Part Of The Format

Skills can include scripts. That makes them useful for deterministic work, but
also means the repo needs a trust model. GitHub Copilot's skill docs warn against
pre-approving shell execution unless the skill and scripts have been reviewed.

This repo should treat script-capable skills as code:

- Review scripts like production code.
- Prefer standard-library helpers when possible.
- Keep tool permissions explicit in harness adapters.
- Do not make shell execution implicit in benchmark cases.

## Prompt Length Anchors

There is no clean public "average developer prompt length" that covers modern
IDE agents, because much of the real prompt includes private editor, repo, chat,
and tool context.

Useful public anchors:

- A 2026 study of transactional prompts in public GitHub repositories reports an
  average prompt length of 560.25 characters, with 69.11% under 500 characters
  and 13.22% at 1,000 characters or longer.
- The same study found software development was one of the top domains in the
  dataset, at 3,863 prompts, or 7.78%.
- DevGPT provides a developer-ChatGPT corpus tied to GitHub artifacts, with
  29,778 prompts and responses in later snapshots. Refactoring-focused studies
  over that data show real developer interactions are often multi-turn and tied
  to commits, issues, pull requests, and code files.

Sources:

- Prompts in the Wild: https://openreview.net/pdf/7bdb8d0207d11aa7e3d07fd81d635c81e0a1fcd2.pdf
- DevGPT: https://arxiv.org/html/2309.03914v2
- ChatGPT for Code Refactoring: https://arxiv.org/html/2509.08090

## Bench Implications

The bench should represent real developer work, not trivia prompts. Strong seed
categories are:

- Repo orientation from a tree, package manifest, issue, or partial docs.
- CI failure triage from logs and changed files.
- PR review triage from diffs and comments.
- Focused code edits with exact constraints.
- Test updates after behavior changes.
- Refactoring with behavior-preservation requirements.
- Documentation synchronization after code changes.

Each case should record both the developer-typed prompt and the estimated full
model input. The prompt can be short while the harness context is large; those
are different skills.

## Repo Direction

Keep these names crisp:

- `check`: structural consistency checks for repo files.
- `bench`: runnable model/harness comparisons.
- `skill`: reusable task workflow packages.
- `harness`: target agent environment and adapter metadata.
- `projection`: generated or symlinked harness-specific skill layout.

Avoid using `validate` for the public interface. It sounds like behavioral
truth, but the current tools only check structure, references, placeholders, and
metadata consistency.
