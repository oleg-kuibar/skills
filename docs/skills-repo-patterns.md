# Skills Repo Patterns

This note keeps the repo aligned with the current agent-skills ecosystem rather
than inventing a private format.

## Package Shape

Modern agent skills converge on a small package:

```text
skill-name/
  SKILL.md
  scripts/
  references/
  assets/
  agents/
```

`SKILL.md` is the routing and workflow entry point. Larger examples, helper
programs, reference documents, and assets live beside it so agents can load them
only when needed.

Sources:

- OpenAI Codex skills: https://developers.openai.com/codex/skills
- Claude Code skills: https://code.claude.com/docs/en/skills
- GitHub Copilot agent skills: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills
- skills.sh docs: https://www.skills.sh/docs

## Install Surface

skills.sh is the install surface for this repo. The CLI supports GitHub shorthands
like `owner/repo`, full Git URLs, direct paths to a skill folder, and local paths.

Useful commands:

```bash
npx skills add oleg-kuibar/skills --list
npx skills add oleg-kuibar/skills --skill vercel-react-best-practices --agent codex --global
npx skills add . --skill verify-this --agent claude-code --global
```

Equivalent package-runner prefixes:

```bash
pnpm dlx skills add oleg-kuibar/skills --list
bunx skills add oleg-kuibar/skills --list
yarn dlx skills add oleg-kuibar/skills --list
```

The CLI also supports `--copy` when symlinks are not appropriate, `--all` for all
skills and agents, and `DISABLE_TELEMETRY=1` to opt out of anonymous install
telemetry.

## Vendoring Instead Of External Symlinks

This repo uses real vendored files generated from `sources.json`. That keeps the
repo installable through `skills.sh` as a self-contained GitHub source while
still making upstream refreshes repeatable.

External symlinks are avoided because they depend on a local sibling checkout
that other users and `skills.sh` will not have. Submodules solve some local Git
tracking problems, but still require submodule-aware cloning and do not make a
plain repository archive self-contained.

To avoid CI failures caused by upstream movement, `sources.json` pins each source
to a commit SHA and records the tracked branch separately. Push and PR checks use
the pinned SHA; a scheduled GitHub workflow checks tracked branches daily and
opens a PR when vendored files should be refreshed.

## Description Is Routing

Skill descriptions are not decorative metadata. They help agents and humans
decide when the skill applies.

Good descriptions should:

- Start with the task trigger.
- Say when to use the skill.
- Avoid broad claims like "helps with coding."
- Keep boundaries explicit enough that unrelated tasks do not activate it.

## Skills Are Not Always-On Instructions

Always-relevant repo rules belong in repo instruction files such as `AGENTS.md`,
custom instructions, or equivalent agent config. Skills are for detailed,
task-specific workflows that should be loaded only when relevant.

That keeps daily agent context smaller and makes the skill library easier to
prune over time.

## Security Is Part Of The Format

Skills can include scripts. That makes them useful for deterministic work, but it
also means the repo needs a trust model.

Treat script-capable skills as code:

- Review scripts like production code.
- Prefer standard-library helpers when possible.
- Keep install commands explicit.
- Avoid granting broad tool permissions inside skill metadata.
