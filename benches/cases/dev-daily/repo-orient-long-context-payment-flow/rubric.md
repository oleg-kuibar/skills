# Rubric

Score out of 10:

- 2 points: Identifies `services/api/src/routes/refunds.ts`,
  `services/api/src/services/refund-retries.ts`, and
  `services/api/src/jobs/retry-refunds.ts` as the first places to inspect.
- 1 point: Names `services/api/tests/refund-retries.test.ts` as the most
  relevant existing test surface.
- 1 point: Extracts `pnpm --filter @acme/api test`, `pnpm -r typecheck`, or
  another package-script-backed check from `package.json`.
- 2 points: Separates evidence from inference and asks for the actual policy
  change before proposing implementation.
- 1 point: Correctly deprioritizes distractors such as email retry docs, search
  indexing retries, currency formatting, and the web billing card.
- 1 point: Calls out idempotency keys, retry attempts, allowed statuses, and max
  retry/backoff as likely policy-sensitive areas.
- 1 point: Suggests a small first move, such as tracing `retryRefund` through the
  queue/job path and adding or updating `refund-retries` tests.
- 1 point: Avoids claiming it inspected files or ran tests beyond the supplied
  context.
