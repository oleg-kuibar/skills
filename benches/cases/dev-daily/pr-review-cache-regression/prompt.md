Use the `pr-review-triage` skill to review this PR diff. Report only actionable
findings.

PR intent:

```text
Avoid duplicate account summary queries by caching account summary responses for
five minutes.
```

Diff:

```diff
diff --git a/src/accounts/summary.ts b/src/accounts/summary.ts
index 2aa1f24..7b313ad 100644
--- a/src/accounts/summary.ts
+++ b/src/accounts/summary.ts
@@ -1,12 +1,22 @@
 import { db } from "../db";
 
+const cache = new Map<string, { expiresAt: number; value: AccountSummary }>();
+
 export async function getAccountSummary(userId: string, accountId: string) {
+  const cached = cache.get(accountId);
+  if (cached && cached.expiresAt > Date.now()) {
+    return cached.value;
+  }
+
   const account = await db.account.findFirst({
     where: {
       id: accountId,
       userId
     },
     include: { invoices: true }
   });
 
-  return summarizeAccount(account);
+  const value = summarizeAccount(account);
+  cache.set(accountId, { expiresAt: Date.now() + 300_000, value });
+  return value;
 }
```
