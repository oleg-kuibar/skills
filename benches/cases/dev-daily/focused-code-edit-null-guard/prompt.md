Use the `focused-code-edit` skill.

Developer prompt:

```text
Make this null-safe.
```

Selected code:

```ts
export function formatCustomerName(customer?: Customer): string {
  return `${customer.firstName} ${customer.lastName}`.trim();
}
```
