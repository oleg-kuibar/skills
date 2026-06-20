# Rubric

Score out of 10:

- 2 points: Identifies the stack as a TypeScript Express service with Vitest,
  ESLint, and `tsc` checks.
- 2 points: Names `src/routes/invoices.ts`, `src/services/invoice-search.ts`,
  and `src/services/csv-export.ts` as likely first files.
- 1 point: Notes tests in `tests/invoice-search.test.ts` and
  `tests/csv-export.test.ts`.
- 1 point: Names `npm test`, `npm run build`, and/or `npm run lint` from
  `package.json` rather than inventing commands.
- 2 points: Separates evidence from inference and calls out missing details such
  as response format, query parameters, escaping rules, or streaming needs.
- 1 point: Suggests a small first move, such as tracing current invoice search
  route behavior before changing export behavior.
- 1 point: Avoids implementing code, claiming tests passed, or inventing files.
