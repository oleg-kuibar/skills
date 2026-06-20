Use the `repo-orient` skill before planning this change.

User request:

```text
We need to add a CSV export for invoice search results. Before touching code,
tell me where you would look first and what checks would matter.
```

Repository snapshot:

```text
.
├── package.json
├── src
│   ├── app.ts
│   ├── routes
│   │   ├── invoices.ts
│   │   └── health.ts
│   ├── services
│   │   ├── invoice-search.ts
│   │   └── csv-export.ts
│   └── db
│       └── invoices.ts
├── tests
│   ├── invoice-search.test.ts
│   └── csv-export.test.ts
└── tsconfig.json
```

`package.json`:

```json
{
  "scripts": {
    "dev": "tsx watch src/app.ts",
    "build": "tsc -p tsconfig.json",
    "test": "vitest run",
    "lint": "eslint src tests"
  },
  "dependencies": {
    "express": "^4.18.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "tsx": "^4.0.0",
    "vitest": "^2.0.0",
    "eslint": "^9.0.0"
  }
}
```

`src/routes/invoices.ts`:

```ts
import { Router } from "express";
import { searchInvoices } from "../services/invoice-search";

export const invoiceRouter = Router();

invoiceRouter.get("/invoices", async (req, res) => {
  const results = await searchInvoices(req.query);
  res.json({ results });
});
```

`src/services/csv-export.ts`:

```ts
export function rowsToCsv(rows: Array<Record<string, unknown>>): string {
  return rows.map((row) => Object.values(row).join(",")).join("\n");
}
```
