# Rubric

Score out of 10:

- 2 points: Uses the `repo-orient` structure or an equivalent concise
  orientation shape.
- 2 points: Does not invent stack, file paths, queues, provider names, or test
  commands that were not supplied by the prompt or harness.
- 2 points: Names plausible file categories to inspect, such as webhook route or
  handler, delivery status persistence, provider response mapping, retry/backoff
  logic, and webhook tests, while marking them as targets rather than facts.
- 1 point: Calls out the key behavioral risk: treating rate limiting as success.
- 1 point: Names useful evidence to gather, such as provider response handling,
  logs around 429 responses, idempotency/retry behavior, and status transition
  tests.
- 1 point: Suggests a small first move focused on tracing the status transition
  path.
- 1 point: Avoids implementing code or claiming any checks passed.
