# Prompt Length Calibration

Bench cases should distinguish the developer-typed prompt from the full model
input assembled by the harness.

## Empirical Anchors

- Google reported an average Transform Code prompt length of 37 characters and
  11 prompts per user per week for an internal natural-language code edit
  feature. This is the micro-edit regime.
- OpenRouter's 100T-token usage study reported average prompt tokens growing
  from about 1.5K in early 2024 to more than 6K in late 2025.
- The same OpenRouter study reports programming workloads as the dominant driver
  of prompt growth, with code understanding, debugging, and generation requests
  routinely exceeding 20K input tokens.
- GitHub Copilot documentation notes that Copilot uses extra context in addition
  to the user's prompt, including the current file and chat history.

Sources:

- Google Transform Code: https://arxiv.org/html/2601.19964v1
- OpenRouter State of AI: https://arxiv.org/html/2601.10088v1
- GitHub Copilot prompt engineering: https://docs.github.com/en/copilot/concepts/prompting/prompt-engineering

## Bench Tiers

| Tier | Developer-typed prompt | Full model input | Use for |
| --- | ---: | ---: | --- |
| `micro-edit` | 1-10 words / roughly 20-80 chars | 500-2,000 tokens | Inline selected-code edits |
| `normal-dev-chat` | 30-150 words | 1,500-6,000 tokens | Ordinary coding chat with limited context |
| `artifact-backed` | 30-150 words plus pasted logs, diffs, or snippets | 1,500-8,000 tokens | CI triage, PR review, repo orientation |
| `long-context-agent` | Short command or normal request | 20,000+ tokens | Agentic repo work with many files, history, and tool state |

## Case Design Rules

1. Record both typed prompt length and full input token estimates in
   `case.json`.
2. Keep `prompt.md` runnable by a human in any harness, even when the case
   represents hidden harness context.
3. For long-context cases, avoid committing huge filler when a compact synthetic
   artifact can exercise the same model behavior. The rubric should test whether
   the model can prioritize relevant context, ignore distractors, and avoid
   claiming it inspected unavailable files.
4. Compare older and newer models within the same tier before drawing broad
   conclusions. Micro-edit performance and long-context agent performance are
   different capabilities.
