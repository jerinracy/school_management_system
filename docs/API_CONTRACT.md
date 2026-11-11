# API Contract & Schema Synchronization Guide

## 1. Overview
The backend DRF OpenAPI 3.0 schema is the single source of truth for all API contracts in the School Management System.
All frontends (React Admin Dashboard, Flutter Mobile App) generate or validate their network clients against this schema.

## 2. Generating the OpenAPI Schema
Run the following command to generate and validate the schema:
```bash
python manage.py spectacular --file schema/schema.yml --validate
```

The validated schema is located at:
`schema/schema.yml`

## 3. Frontend Client Synchronization (React Dashboard)
Inside the `frontend/` directory, the TypeScript API client is generated using `openapi-typescript`:
```bash
npm run gen:api
```
This regenerates `src/types/api.ts` from `../schema/schema.yml`. Manual editing of generated types is strictly forbidden.

## 4. Mobile Client Synchronization (Flutter)
Inside the Flutter repository, models and Dio client contracts are generated or validated against `schema.yml`:
```bash
dart run build_runner build --delete-conflicting-outputs
```

## 5. Contract Change Rules
1. Every new or updated endpoint must be decorated with `@extend_schema` from `drf_spectacular.utils`.
2. Breaking changes require a version bump (e.g., `/api/v2/`) or a documented deprecation cycle.
3. CI automatically enforces schema validity with `python manage.py spectacular --validate`.
