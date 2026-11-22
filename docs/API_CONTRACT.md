# API Contract & Schema Synchronization Guide

## 1. Overview
The backend DRF OpenAPI 3.0 schema is the single source of truth for all API contracts in the School Management System.
All frontends (React Admin Dashboard, Flutter Mobile App) generate or validate their network clients against this schema (`schema/schema.yml`).

## 2. Generating & Validating the OpenAPI Schema
Run the following command to generate and validate the schema:
```bash
# Using project virtualenv:
venv/bin/python manage.py spectacular --file schema/schema.yml --validate

# Or with activated virtualenv:
python manage.py spectacular --file schema/schema.yml --validate
```

The validated schema is located at:
`schema/schema.yml`

Interactive schema viewers are available at:
- Swagger UI: `GET /api/docs/`
- ReDoc: `GET /api/redoc/`
- Raw OpenAPI schema: `GET /api/schema/`

## 3. Frontend Client Synchronization (React Dashboard)
Inside the `frontend/` directory, the TypeScript API client and component prop schemas are generated using `openapi-typescript`:
```bash
cd frontend
npm run gen:api
```
This regenerates `frontend/src/types/api.ts` directly from `../schema/schema.yml`. Manual editing of generated types is strictly forbidden.

After regenerating types, run type checking to verify full compile-time compliance:
```bash
cd frontend
npm run typecheck
```

## 4. Mobile Client Synchronization (Flutter)
Inside the Flutter mobile application repository, data transfer objects (DTOs), models, and typed network repositories are generated and validated against `schema/schema.yml`:

### Recommended Generation Command
```bash
# If using openapi-generator or custom schema code generation:
dart run build_runner build --delete-conflicting-outputs
```

### Mobile Contract Guidelines
1. **Never hand-write request or response models**: All network models in Flutter must match OpenAPI schema definitions or be generated using `freezed` / `json_serializable` mapped to the OpenAPI properties.
2. **Standard Error Envelope**: All API errors conform to the standard error envelope:
   ```json
   {
     "code": "ERROR_CODE",
     "message": "Human-readable description",
     "details": {}
   }
   ```
   Map HTTP status codes and `code` strings to strongly typed Dart `Failure` classes in the mobile app.
3. **Date, Time & Timezone**:
   - Dates are formatted as `YYYY-MM-DD`.
   - Datetimes are serialized as ISO 8601 strings (e.g., `2026-11-19T14:30:00+06:00`).
   - Store in UTC, format and display in `Asia/Dhaka` (`UTC+6`).
4. **Money / Amounts**:
   - Currency is Bangladeshi Taka (`BDT`, symbol `৳`).
   - Serialized as decimal strings (e.g., `"1500.00"`).
   - Parse using `Decimal` in Dart or calculate in integer paisa (`* 100`) to prevent IEEE 754 floating point inaccuracies.

## 5. Contract Change Rules & Policies
1. **Contract-First**: Every new or updated endpoint must be decorated with `@extend_schema` from `drf_spectacular.utils`.
2. **Backward Compatibility**: Non-breaking additive changes (new endpoints, optional query parameters, additional response fields) are added under `/api/v1/`.
3. **Breaking Changes**: Any breaking changes to existing endpoints require a new API version (e.g., `/api/v2/`) or a documented deprecation cycle.
4. **CI Enforcement**: Continuous Integration automatically validates schema generation with `python manage.py spectacular --validate`.
