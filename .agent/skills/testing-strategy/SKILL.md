---
name: testing-strategy
description: Use in Phase 1 to define the test plan and in Phase 2–3 to write and run tests. Ensures every task ships with unit, integration, permission, and edge-case tests.
---

# testing-strategy

### Test pyramid per task
- **Unit:** pure logic (services, grade calculation, late/half-day rules, fee fine calculation).
- **Integration:** API endpoints with DB (Django) / repository + fake datasource (Flutter) / hooks + MSW (React).
- **Permission matrix tests:** for each endpoint, test allowed role, denied role, unauthenticated, other-tenant user.
- **Contract tests:** schema validates (`spectacular --validate`); generated clients compile.
- **E2E (few, critical):** login → admit student → take attendance → collect fee → publish result.

### Must-have cases
- Boundary values (marks 32/33, grace minutes, 0/100).
- Idempotency (duplicate payment webhook, duplicate punch).
- Concurrency (two receipts generated simultaneously → no duplicate numbers).
- Time zones & Friday/holiday logic.
- Bangla text (names, search, PDF generation).
- Empty / huge data sets, pagination edges.

### Tooling
- Django: pytest, pytest-django, factory_boy, freezegun, `django_assert_num_queries`, responses/respx for gateways.
- React: Vitest, RTL, MSW, Playwright, axe for a11y.
- Flutter: flutter_test, mocktail, golden tests, integration_test.

### Rules
- Test names describe behaviour: `test_late_if_punch_after_grace_period`.
- No test depends on another test's state.
- Report real results; flaky tests are fixed or quarantined with a ticket, never ignored.

---
