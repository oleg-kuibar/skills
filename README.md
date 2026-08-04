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
- `sources.json` is the source of truth for vendored upstream files. Its `owned`
  array lists files written here, which have no upstream to pin or diff.
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

## Token discipline agents

`locate` and `check` are Haiku subagents that keep file contents and clean tool
output out of the main session. `locate` answers "where is X" with paths and line
ranges. `check` runs the project's own typecheck, lint, and tests and returns only
the failures as `path:line message`. A clean run costs one line.

They came out of measuring where my own Claude Code tokens went across 281
sessions. Both are read-only.

`park` writes the live state of a conversation to a gitignored file beside the
work, keyed on the branch, so the session can be cleared and the next one picks
it up. It needs a one-time hook install, Claude Code only:

```bash
/usr/bin/python3 ~/.claude/skills/park/scripts/handoff-pickup.py --install
```

That symlinks the script into `~/.claude/hooks/` and adds a `SessionStart` hook
to `~/.claude/settings.json`, leaving your other settings and hooks alone.
Re-running it is safe. The script has its own check: `--selftest`.

The hook fires on a new session, on `/clear`, and on compaction, which drops a
parked handoff the same way a clear does. A handoff older than three days is
injected with a line saying how old it is.

The parked file holds whatever the session had in context. It is hidden by a
`.gitignore` inside `.claude/handoff/`, but the redaction of secrets is done by
the model, not enforced by the script.

## Add a Skill

Vendored from upstream: add an entry to `sources.json` with a pinned commit SHA
and a `target` under `skills/` or `agents/`, then refresh:

```bash
python3 tools/sync_sources.py
```

Written here: add the path to the `owned` array in `sources.json` instead. Nothing
to sync.

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
