---
name: api-contract-openapi
description: Use when creating/changing endpoints or when a client (dashboard/Flutter) consumes the API. Keeps the OpenAPI schema as the single source of truth and the clients in sync.
---

# api-contract-openapi

### Procedure
1. Annotate views with `@extend_schema` (request, responses, params, error examples).
2. Generate schema: `python manage.py spectacular --file schema/openapi.yml --validate`; commit it.
3. **Dashboard:** `npm run gen:api` → regenerate TypeScript types/client from `schema/openapi.yml`.
4. **Flutter repo:** copy `openapi.yml` (or fetch from a tagged release) into `api_contract/openapi.yml` and regenerate the Dart client / DTOs; record schema version in `api_contract/VERSION`.
5. Classify changes: **additive** (OK) / **breaking** (needs `/v2/` or compatibility period) — mention in the report.
6. Error format: `{ "code": "attendance.device_not_found", "message": "...", "details": {...} }`; keep code list in `docs/API_CONTRACT.md`.
7. Pagination: `{count, next, previous, results}` (page-number or cursor — decide once in Task 01).
8. Version header for app compatibility: `X-App-Version`; server may return `426` with a minimum version message for forced updates.

---
