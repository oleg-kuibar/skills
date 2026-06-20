# Rubric

Score out of 10:

- 2 points: Identifies `npm test` / `vitest run` as the failing command and
  `tests/invoice-total.test.ts` as the failing test location.
- 2 points: Explains that `voided` invoices are currently included because the
  filter only excludes `paid`.
- 2 points: Proposes the smallest fix direction: include only `open` invoices or
  explicitly exclude both `paid` and `voided`, depending on domain intent.
- 1 point: Distinguishes root cause from general CI noise.
- 1 point: Names `npm test -- tests/invoice-total.test.ts` or `npm test` as a
  verification command without claiming it has passed.
- 1 point: Mentions that domain rules should confirm whether other statuses must
  be excluded.
- 1 point: Avoids unrelated dependency, environment, or snapshot explanations.
