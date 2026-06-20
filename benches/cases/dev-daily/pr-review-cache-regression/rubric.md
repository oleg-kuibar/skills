# Rubric

Score out of 10:

- 4 points: Finds the cache key bug: caching only by `accountId` can return a
  summary without rechecking `userId`, creating a cross-user data leak if account
  ids are guessable, reused across tenants, or authorization assumptions change.
- 2 points: Grounds the finding in the changed lines that call `cache.get` before
  the database query and use `accountId` as the sole key.
- 1 point: Gives appropriate severity, ideally `P1` for possible data exposure.
- 1 point: Suggests a concrete fix such as keying by both `userId` and
  `accountId`, or caching only after an authorization-aware lookup with a scoped
  key.
- 1 point: Calls out a missing regression test for two users requesting the same
  account id or scoped cache behavior.
- 1 point: Avoids low-signal style comments or claiming the whole PR is broken
  beyond the evidenced finding.
