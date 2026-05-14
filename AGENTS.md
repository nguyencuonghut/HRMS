# Project Instructions

## Core Rules

- Never guess. Every conclusion must be backed by code inspection, command output, tests, or direct runtime verification.
- If something has not been verified yet, say so explicitly instead of inferring.

## Verification Gates

### Backend-only changes

- Verify the touched behavior with automated tests at the narrowest correct seam.
- If the change affects database queries or seed data, also run a direct runtime check against the running backend or DB state.

### Frontend-only changes

- `npm run build` is required but never sufficient for user-visible behavior.
- If the change affects layout, rendering, filtering, async state, form flow, routing, or component interaction, also verify it in a browser-level loop.

### Full-stack changes

- Verify both seams:
  - backend contract/data seam
  - browser/UI seam
- Do not conclude success from passing API tests alone when the user-visible behavior depends on frontend state or event timing.

### Bug fixes

- Reproduce the bug first with a deterministic loop when possible.
- Add a regression check at the seam where the bug actually appeared.
- Re-run the original repro loop after the fix.

## Required Browser-Level Verification Cases

Use browser-level verification for any task that changes:

- filters, selects, search boxes, pagination, sorting
- async loading or state synchronization
- conditional rendering / empty states
- router navigation
- dialogs, drawers, modals
- CRUD flows visible to the user

Preferred check order:

1. Interact with the page
2. Assert on visible DOM state
3. Inspect relevant network requests/responses when needed

## Final Response Requirements

- State exactly what was verified.
- State exactly what was not verified.
- Do not present an assumption as a fact.
