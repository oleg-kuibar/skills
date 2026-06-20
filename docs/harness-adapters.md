# Harness Adapters

Harness adapters translate canonical skills and prompts into the environment an
agent actually sees.

Adapters should be thin:

- Keep the canonical skill text unchanged unless the harness cannot consume it.
- Record any transformation that could affect model behavior.
- Keep generated projections out of the canonical skill folder unless they are
  the harness' required metadata, such as Codex `agents/openai.yaml`.
- Store local run outputs under `runs/`, not inside `skills/` or `benches/`.

## Initial Harnesses

- `codex`: Coding-agent harness with local workspace access.
- `claude-code`: Coding-agent harness target for future adapter work.
- `pi`: Conversational assistant harness target for future adapter work.

The manifests in `harnesses/` are the current source of truth for adapter status.
