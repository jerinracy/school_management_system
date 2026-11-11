---
name: react-spa-dashboard
description: Use for any React/TypeScript dashboard work inside the Django repo's frontend/ folder: pages, forms, tables, data fetching, routing, i18n, permissions, and tests.
---

# react-spa-dashboard

### Patterns
- **Structure:** `features/<module>/{api,components,pages,hooks,schemas,types}`; shared `components/ui`, `lib`, `routes`.
- **Data:** TanStack Query hooks per resource: `useStudents(filters)`, `useCreateStudent()`; query keys factory; invalidate precisely on mutation; optimistic updates only where safe.
- **Forms:** React Hook Form + Zod; map server field errors back to fields; disable submit while pending; confirm unsaved changes.
- **Tables:** one reusable `DataTable` (server pagination/sort/filter, column visibility, CSV export hook, row actions, bulk select).
- **Permissions:** `usePermission("students.add")`, `<Can perm="...">`, route guards from `/me/permissions`.
- **Auth:** access token in memory, refresh via httpOnly cookie or secure refresh flow (decide in Task 03); automatic refresh on 401 once; logout everywhere on refresh failure.
- **i18n:** namespaces per feature; ICU plurals; `Intl.NumberFormat("bn-BD")` and `bn` date formatting with Bangla/English toggle.
- **Charts:** Recharts; every chart has a table/aria fallback.
- **Printing:** print-optimised routes for ID cards, admit cards, receipts, marksheets (CSS `@page`, Bangla fonts).
- **Error boundaries** per route; toast for transient, inline for validation.
- **Testing:** RTL for components, MSW for API, Playwright for critical flows.

### Rules
- Never trust UI hiding for security.
- No `any`; no unused deps; lazy-load heavy routes.
- Keep components < ~200 lines; extract hooks.

---
