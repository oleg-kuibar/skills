Use the `ci-failure-triage` skill to diagnose this CI failure. Do not write the
patch yet.

CI log excerpt:

```text
Run npm test

> billing-api@0.4.0 test
> vitest run

 FAIL  tests/invoice-total.test.ts > invoice totals > ignores voided invoices
AssertionError: expected 13500 to be 9000

Expected: 9000
Received: 13500

  tests/invoice-total.test.ts:18:35
    16|   ]);
    17|
    18|   expect(totalOpenInvoices(rows)).toBe(9000);
      |                                   ^
    19| });

Test Files  1 failed | 23 passed
Tests       1 failed | 118 passed
```

Recently changed code:

```ts
export function totalOpenInvoices(rows: InvoiceRow[]): number {
  return rows
    .filter((row) => row.status !== "paid")
    .reduce((sum, row) => sum + row.amountCents, 0);
}
```

Test data:

```ts
const rows = [
  { id: "inv_1", status: "open", amountCents: 9000 },
  { id: "inv_2", status: "voided", amountCents: 4500 },
  { id: "inv_3", status: "paid", amountCents: 2000 }
];
```
