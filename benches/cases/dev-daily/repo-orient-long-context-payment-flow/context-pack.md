# Context Pack

This case represents a long-context coding-agent session. The committed fixture
is compact, but the case metadata calibrates the intended full input as a
20K-30K token workload after harness instructions, skills, open files, chat
history, and tool state are included.

## User Goal

Change refund retry behavior. The user has not asked for an implementation yet;
they asked where to start.

## File Tree Excerpt

```text
.
├── package.json
├── services
│   ├── api
│   │   ├── src/routes/payments.ts
│   │   ├── src/routes/refunds.ts
│   │   ├── src/services/payment-intents.ts
│   │   ├── src/services/refund-retries.ts
│   │   ├── src/services/refund-state.ts
│   │   ├── src/jobs/retry-refunds.ts
│   │   └── tests/refund-retries.test.ts
│   ├── worker
│   │   ├── src/queues/refund-queue.ts
│   │   └── src/handlers/refund-events.ts
│   └── web
│       ├── src/routes/settings.tsx
│       └── src/components/BillingCard.tsx
├── packages
│   ├── money/src/currency.ts
│   ├── telemetry/src/events.ts
│   └── config/src/flags.ts
└── docs
    ├── payments.md
    ├── email-delivery.md
    └── search-indexing.md
```

## package.json

```json
{
  "scripts": {
    "build": "pnpm -r build",
    "test": "pnpm -r test",
    "test:api": "pnpm --filter @acme/api test",
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r typecheck"
  }
}
```

## Relevant Snippets

`services/api/src/routes/refunds.ts`

```ts
router.post("/refunds/:id/retry", async (req, res) => {
  const result = await retryRefund(req.params.id, req.user.id);
  res.json({ result });
});
```

`services/api/src/services/refund-retries.ts`

```ts
export async function retryRefund(refundId: string, userId: string) {
  const refund = await findRefundForUser(refundId, userId);
  if (!refund) {
    throw new NotFoundError("Refund not found");
  }
  if (refund.status !== "failed") {
    throw new InvalidStateError("Only failed refunds can be retried");
  }
  await enqueueRefundRetry({ refundId, attempt: refund.retryAttempt + 1 });
  return markRefundRetryQueued(refundId);
}
```

`services/api/src/jobs/retry-refunds.ts`

```ts
export async function processRefundRetry(job: RefundRetryJob) {
  const refund = await getRefund(job.refundId);
  const response = await payments.refund({
    chargeId: refund.chargeId,
    amount: refund.amountCents,
    idempotencyKey: `refund:${refund.id}:attempt:${job.attempt}`
  });
  return applyRefundGatewayResponse(refund.id, response);
}
```

`services/api/tests/refund-retries.test.ts`

```ts
it("queues a retry for failed refunds", async () => {
  const refund = await givenRefund({ status: "failed", retryAttempt: 0 });
  await retryRefund(refund.id, refund.userId);
  expect(await queuedRefundRetries()).toContainEqual({
    refundId: refund.id,
    attempt: 1
  });
});
```

## Distractor Context

The web settings page has a billing card but does not own refund state.
`docs/email-delivery.md` mentions retry policies for email notifications.
`docs/search-indexing.md` mentions retrying failed indexing batches.
`packages/money/src/currency.ts` handles currency formatting only.
`packages/telemetry/src/events.ts` emits event names but does not decide retry
behavior.

## Prior Session Notes

- A previous agent inspected `services/web/src/components/BillingCard.tsx` and
  concluded the UI might need a new button. That was premature because the user
  asked about retry behavior, not UI.
- A previous test failure involved email retry backoff. It is unrelated unless
  the same queue abstraction is reused, which is not shown in this context.
- The relevant unknown is the desired policy change: allowed statuses, max
  attempts, backoff, idempotency, and whether manual and scheduled retries share
  rules.
