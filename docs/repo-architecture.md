# Repo Architecture

This repo separates three concerns that are easy to mix together:

1. Canonical user skills
2. Harness-specific projection
3. Benchmark evidence

## Canonical Skills

`skills/<skill-name>/SKILL.md` is the source of truth for a developer skill.
Write it so an agent can use it without knowing which harness it is running in.
Prefer stable instructions, explicit constraints, and reusable resources over
harness-specific phrasing.

Skill folders may include:

- `agents/openai.yaml` for Codex UI metadata
- `scripts/` for deterministic helper programs
- `references/` for context loaded only when needed
- `assets/` for reusable output files

Harness-specific copies, generated projections, and run outputs should not become
the source of truth.

## Harness Manifests

`harnesses/*.json` records what a harness is and how skills are expected to be
projected into it. These manifests are intentionally small. They should describe
capabilities, adapter status, and known caveats without encoding live secrets,
model names, or environment-local paths.

Use harness manifests to keep comparisons honest:

- Which harness ran the prompt?
- Which skill projection was used?
- Which limitations belong to the harness rather than the model?
- Which adapter still needs implementation?

## Bench Cases

`benches/cases/<suite>/<case>/` stores a stable prompt and rubric. A case should
be runnable against old and new models with the same user-facing prompt and the
same canonical skills.

Cases should come from real developer daily work: reviewing diffs, orienting to a
repo, diagnosing CI, planning a small patch, addressing review feedback,
debugging a regression, writing tests, or summarizing technical tradeoffs from
project artifacts. Avoid cases whose only value is generic text cleanup.

Each case has:

- `case.json` for metadata and references
- `prompt.md` for the exact user prompt
- `rubric.md` for human or automated scoring criteria

Suites in `benches/suites/` group cases into meaningful runs such as rudimentary
skill use, longer workflow behavior, or harness-adapter stress tests.

## Runs

`runs/` is ignored by git. Put local run outputs there using a path such as:

```text
runs/<date>/<harness>/<model>/<suite>/<case>/
```

A run folder can contain transcripts, artifacts, model metadata, grader notes,
and diffs against prior models. Commit only the bench case and rubric unless a
particular run result is intentionally promoted into documentation.
