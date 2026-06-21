# Skills

[![skills.sh](https://skills.sh/b/oleg-kuibar/skills)](https://skills.sh/oleg-kuibar/skills)

Personal agent skills I use for daily developer work, installed directly through
[skills.sh](https://www.skills.sh/docs).

Benchmarks and eval cases belong in a separate repo. This repo is intentionally
just the reusable skill library and install path. Keep only skills and agents
that are actually useful enough to keep using.

## Layout

```text
skills/
  skill-name/
    SKILL.md
    agents/openai.yaml
    scripts/
    references/
    assets/
skills.sh.json  # optional, once there are enough real skills to group
sources.json
agents/
  agent-name.md
tools/
```

- `skills/` contains canonical developer skill sources. Keep each skill lean:
  concise instructions in `SKILL.md`, deterministic helpers in `scripts/`,
  detailed context in `references/`, and reusable output assets in `assets/`.
- `agents/` contains installable agent definitions that are not skills.
- `skills.sh.json` is optional. Add it when there are enough real skills to group
  on the skills.sh repo page.
- `sources.json` declares which upstream files are vendored into this repo.
- `tools/` contains the source sync/check script used by CI.

See [docs/repo-architecture.md](docs/repo-architecture.md) for the organizing
principles and [docs/skills-repo-patterns.md](docs/skills-repo-patterns.md) for
the external skill-repo patterns this layout is tracking.

## Install Skills

The official examples use `npx`, but any package runner that can execute npm
packages works. Pick the one you already use:

```bash
npx skills add oleg-kuibar/skills --list
pnpm dlx skills add oleg-kuibar/skills --list
bunx skills add oleg-kuibar/skills --list
yarn dlx skills add oleg-kuibar/skills --list
```

List the skills in this repo:

```bash
npx skills add oleg-kuibar/skills --list
```

Install every skill globally for Codex:

```bash
npx skills add oleg-kuibar/skills --skill '*' --agent codex --global --yes
```

Install one skill globally for Codex:

```bash
npx skills add oleg-kuibar/skills --skill vercel-react-best-practices --agent codex --global
```

Install one skill globally for Claude Code:

```bash
npx skills add oleg-kuibar/skills --skill verify-this --agent claude-code --global
```

Install into the current project instead of your global agent directory:

```bash
npx skills add oleg-kuibar/skills --skill fix-merge-conflicts --agent codex
```

Use a local checkout while editing:

```bash
npx skills add . --skill vercel-composition-patterns --agent codex --global
```

The skills.sh CLI collects anonymous install telemetry by default. Set
`DISABLE_TELEMETRY=1` if you want to opt out.

## Create a Skill

```bash
npx skills init skills/my-skill
```

Then edit `skills/my-skill/SKILL.md` so the frontmatter description clearly
states what the skill does and when an agent should use it. Add optional
resource folders when they are genuinely useful:

```bash
mkdir -p skills/my-skill/scripts skills/my-skill/references skills/my-skill/assets
```

If the repo eventually has enough skills to group on skills.sh, add
`skills.sh.json`.

## Current Library

Skills:

- `vercel-react-best-practices` from [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices)
- `vercel-composition-patterns` from [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills/tree/main/skills/composition-patterns)
- `verify-this` from [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/verify-this)
- `weekly-review` from [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/weekly-review)
- `fix-merge-conflicts` from [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/fix-merge-conflicts)
- `thermo-nuclear-code-quality-review` from [cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review)
- `grill-with-docs` from [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs)
- `domain-modeling` from [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling)

Agents:

- `thermo-nuclear-code-quality-review` from [cursor/plugins](https://github.com/cursor/plugins/blob/main/cursor-team-kit/agents/thermo-nuclear-code-quality-review.md)

## Credits

This repo vendors skills and agents from public upstream repositories so
`skills.sh` can install this collection from one self-contained source. The
source of truth for those vendored copies is [sources.json](sources.json).

- [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)
  - [react-best-practices](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices)
  - [composition-patterns](https://github.com/vercel-labs/agent-skills/tree/main/skills/composition-patterns)
- [cursor/plugins](https://github.com/cursor/plugins)
  - [verify-this](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/verify-this)
  - [weekly-review](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/weekly-review)
  - [fix-merge-conflicts](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/fix-merge-conflicts)
  - [thermo-nuclear-code-quality-review skill](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review)
  - [thermo-nuclear-code-quality-review agent](https://github.com/cursor/plugins/blob/main/cursor-team-kit/agents/thermo-nuclear-code-quality-review.md)
- [mattpocock/skills](https://github.com/mattpocock/skills)
  - [grill-with-docs](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs)
  - [domain-modeling](https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling)

The vendored copies are intentionally real files generated from `sources.json`,
rather than symlinks to sibling checkouts. Symlinks to external repos would be
convenient locally, but they would break for anyone installing this GitHub repo
through `skills.sh` without the same local directory layout.

Refresh vendored files from upstream:

```bash
python3 tools/sync_sources.py
```

Check that vendored files still match upstream:

```bash
python3 tools/sync_sources.py --check
```

Check upstream tracked branches and refresh pinned refs:

```bash
python3 tools/sync_sources.py --update --report /tmp/vendored-skills-update.md
```

`sources.json` pins every vendored source to a commit SHA for stable installs and
CI checks. The `track` field records the upstream branch checked by the scheduled
GitHub workflow.

## Check Sources

```bash
python3 tools/sync_sources.py --check
```

The check verifies that vendored files match `sources.json`, that skills and
agents are declared in the manifest, and that frontmatter plus `skills.sh.json`
are structurally valid.

GitHub Actions also runs a daily scheduled update at `09:17 UTC`. When upstream
sources move, the workflow updates `sources.json`, regenerates vendored files,
and opens or updates the `automation/update-vendored-skills` pull request.
