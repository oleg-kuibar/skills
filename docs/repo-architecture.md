# Repo Architecture

This repository is a personal agent skills and agents library. It has three
responsibilities:

1. Keep reusable skills and agents in one canonical place.
2. Make them easy to install through skills.sh.
3. Keep vendored upstream content reproducible through `sources.json`.

Benchmarks, eval suites, model comparisons, and harness adapters should live in a
separate repository.

The repo should contain only skills and agents that are actually used. Seed
examples and bench leftovers should not remain in `skills/` or `agents/`.
Vendored files should be refreshed with `python3 tools/sync_sources.py`, not
edited by hand unless the change is intentionally local.

## Canonical Skills

`skills/<skill-name>/SKILL.md` is the source of truth for each skill. Write it so
an agent can use it without knowing which install target it is running in.

Skill folders may include:

- `agents/openai.yaml` for Codex UI metadata.
- `scripts/` for deterministic helper programs.
- `references/` for detailed context loaded only when needed.
- `assets/` for reusable output files.

Keep `SKILL.md` concise. Put longer examples and supporting material beside it
instead of turning the entry point into a long manual.

## Agents

`agents/<agent-name>.md` contains agent definitions that are useful to keep next
to the skills they depend on. Agent frontmatter should include `name` and
`description`, and the `name` must match the file stem.

## Installation

The public install path is the skills.sh CLI:

```bash
npx skills add oleg-kuibar/skills --skill vercel-react-best-practices --agent codex --global
```

Use the same command shape with your preferred package runner:

```bash
pnpm dlx skills add oleg-kuibar/skills --skill vercel-react-best-practices --agent codex --global
bunx skills add oleg-kuibar/skills --skill vercel-react-best-practices --agent codex --global
yarn dlx skills add oleg-kuibar/skills --skill vercel-react-best-practices --agent codex --global
```

## Source Sync

`sources.json` declares every vendored skill and agent: upstream repo, pinned
commit SHA, tracked branch, source path, target path, and optional include globs.
The sync script clones those upstreams to a temporary directory and copies the
selected files into this repo.

Refresh vendored files:

```bash
python3 tools/sync_sources.py
```

Verify vendored files match upstream:

```bash
python3 tools/sync_sources.py --check
```

Check tracked branches and update pinned refs:

```bash
python3 tools/sync_sources.py --update --report /tmp/vendored-skills-update.md
```

Normal CI only compares against pinned `ref` values. The scheduled GitHub
workflow runs daily at `09:17 UTC` to check `track` branches and open/update a
reviewable PR when upstream content changes.

## Repo Page Metadata

`skills.sh.json` controls grouping on the skills.sh repository page. It does not
change skill contents or install behavior. Keep it out of the repo until there
are real skills to group.

When a skill is added or removed, update `skills.sh.json` so the public page
stays readable.

## Checks

`python3 tools/sync_sources.py --check` verifies:

- Vendored files match `sources.json`.
- Skills and agents are declared in `sources.json`.
- Source refs are pinned to commit SHAs.
- Skill folder names.
- Required `SKILL.md` frontmatter.
- Non-empty skill bodies.
- Agent markdown frontmatter.
- Optional `skills.sh.json` shape and skill references.
- Placeholder cleanup in strict mode.

The check is structural only. It does not prove that a skill is useful; actual
quality comes from using the skills in real work and pruning anything that does
not earn its place.
