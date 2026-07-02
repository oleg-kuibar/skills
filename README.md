# Skills

[![skills.sh](https://skills.sh/b/oleg-kuibar/skills)](https://skills.sh/oleg-kuibar/skills)

Personal agent skills I use for daily developer work, installed through
[skills.sh](https://www.skills.sh/docs).

Benchmarks, eval cases, and broad candidate backlogs belong elsewhere. This repo
is just the installable skill and agent library.

## Layout

```text
skills/
  skill-name/
    SKILL.md
    scripts/
    references/
    assets/
agents/
  agent-name.md
skills.sh.json
sources.json
tools/
```

- `skills/` contains installable skills.
- `agents/` contains installable agent definitions that are not skills.
- `skills.sh.json` groups the public skills.sh repo page.
- `sources.json` is the source of truth for vendored upstream files.
- `tools/sync_sources.py` refreshes or checks those vendored files.

## Install

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

Use a local checkout while editing:

```bash
npx skills add . --skill vercel-composition-patterns --agent codex --global
```

The skills.sh CLI collects anonymous install telemetry by default. Set
`DISABLE_TELEMETRY=1` to opt out.

## Add a Skill

Add an entry to `sources.json` with a pinned commit SHA and a `target` under
`skills/` or `agents/`, then refresh:

```bash
python3 tools/sync_sources.py
```

## Check

Check that vendored files still match `sources.json`:

```bash
python3 tools/sync_sources.py --check
```

Check that skills.sh can read the package:

```bash
DISABLE_TELEMETRY=1 npx --yes skills add . --list
```

To update vendored upstream content, change the pinned `ref` in `sources.json`
and run `python3 tools/sync_sources.py`.
