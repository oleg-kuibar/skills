# Bench Case Schema

Bench cases live at:

```text
benches/cases/<suite-id>/<case-id>/
```

Each case folder must contain `case.json`, `prompt.md`, and `rubric.md`.

## case.json

Required fields:

- `id`: `<suite-id>/<case-id>`
- `title`: Short human-readable name
- `suite`: Suite id matching the parent folder
- `objective`: What behavior the case measures
- `work_type`: Real developer activity being tested, such as `code-review`,
  `ci-triage`, `repo-orientation`, or `patch-planning`
- `artifact_types`: Developer artifacts included in or required by the case,
  such as `pull-request-diff`, `ci-log`, `file-tree`, or `source-snippet`
- `prompt_profile`: Prompt-length calibration metadata. This separates the
  prompt the developer would type from the full model input after a harness adds
  skills, selected code, repo context, logs, diffs, history, and tool state.
- `harnesses`: Harness ids that should be able to run the case
- `skill_refs`: Canonical skill ids required by the prompt. Bench cases should
  use at least one real reusable skill.
- `prompt`: Usually `prompt.md`
- `rubric`: Usually `rubric.md`
- `tags`: Searchable labels
- `inputs`: Stable environment assumptions
- `expected_outputs`: Output features the evaluator should look for
- `evaluation`: Scoring mode and maximum score

Keep prompts user-like and based on normal developer work. Put evaluator-only
expectations in `rubric.md`, not in the prompt.

## prompt_profile

Required fields:

- `developer_prompt_tier`: One of `micro-edit`, `normal-dev-chat`,
  `artifact-backed`, or `long-context-agent`
- `developer_prompt_chars`: Approximate characters intentionally typed by the
  developer, excluding harness-added context
- `developer_prompt_words`: Approximate words intentionally typed by the
  developer, excluding harness-added context
- `full_input_token_range`: Object with positive integer `min` and `max`
  estimates for the full model input
- `calibration`: Short explanation of which empirical tier this case targets

Use the tiers from [prompt-length-calibration.md](prompt-length-calibration.md).

## Scoring

Prefer rubrics that separate:

- Skill discovery and use
- Instruction following
- Factual or artifact correctness
- Harness/tool awareness
- Unwarranted invention
- Recovery from ambiguity

This makes it easier to tell whether a prompt, skill, adapter, system prompt, or
model family needs adjustment.
