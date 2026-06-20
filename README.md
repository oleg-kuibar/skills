# Skills Bench

This repository keeps reusable developer skills, harness adapters, and benchmark
cases for comparing how different agents and model generations behave with the
same prompts and skill material.

The main rule: base benches on real daily developer work and real reusable skills,
then project the same skill and prompt into Codex, Claude Code, Pi, or any later
harness with the smallest adapter needed for that harness.

## Layout

```text
skills/
  skill-name/
    SKILL.md
    agents/openai.yaml
    scripts/
    references/
    assets/
harnesses/
  codex.json
  claude-code.json
  pi.json
benches/
  suites/
  cases/
    suite-id/
      case-id/
        case.json
        prompt.md
        rubric.md
runs/
tools/
```

- `skills/` contains canonical developer skill sources. Keep each skill lean:
  concise instructions in `SKILL.md`, deterministic helpers in `scripts/`,
  detailed context in `references/`, and reusable output assets in `assets/`.
- `harnesses/` describes each target environment without assuming all harnesses
  have the same skill-loading or tool model.
- `benches/` contains stable developer-work cases, prompts, and rubrics that can
  be run against multiple harnesses and model versions. Seed suites should use
  artifacts like diffs, logs, repo snapshots, issue reports, review comments, and
  failing tests, not abstract toy transformations.
- Bench cases record `prompt_profile` metadata so runs can compare micro-edit,
  normal chat, artifact-backed, and long-context agent prompts separately.
- `runs/` is intentionally ignored. Store local run outputs there while comparing
  model behavior.

See [docs/repo-architecture.md](docs/repo-architecture.md) for the organizing
principles, and [docs/prompt-length-calibration.md](docs/prompt-length-calibration.md)
for the prompt-length tiers. See
[docs/skills-repo-patterns.md](docs/skills-repo-patterns.md) for the external
skill-repo patterns this layout is tracking.

## Create a Skill

```bash
python3 tools/init_skill.py my-skill
```

Add optional resource folders when they are genuinely useful:

```bash
python3 tools/init_skill.py my-skill --resources scripts,references,assets
```

After scaffolding, edit `skills/my-skill/SKILL.md` so the frontmatter description
clearly states what the skill does and when an agent should use it.

## Create a Bench Case

```bash
python3 tools/init_bench_case.py dev-daily/my-case \
  --skills repo-orient \
  --work-type repo-orientation \
  --artifact-types file-tree,source-snippet
```

The script registers the case in `benches/suites/<suite>.json`. Then fill in
`case.json`, `prompt.md`, and `rubric.md`. If the suite file was created from
scratch, fill in its title and description too. Cases should avoid harness-specific
assumptions unless the point of the case is to test an adapter.

## Check Structure

```bash
python3 tools/check_structure.py --strict
```

The structural check verifies schemas, references, prompt-length metadata, and
placeholder cleanup. It does not run model prompts or score model behavior.

Strict checks fail on placeholders in committed skills, harness manifests, and
bench cases. Use loose checks while drafting:

```bash
python3 tools/check_structure.py
```

## Install for Codex

Codex discovers personal skills from `${CODEX_HOME:-$HOME/.codex}/skills`. To
symlink a canonical skill from this repo into that directory:

```bash
python3 tools/install_skill.py repo-orient
```

Use `--copy` instead of the default symlink when you need an independent snapshot.
