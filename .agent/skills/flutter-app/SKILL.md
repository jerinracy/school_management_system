---
name: flutter-app
description: Use for any Flutter work: features, screens, state management, navigation, API integration, theming, l10n, and platform configuration in the separate mobile repo.
---

# flutter-app

### Patterns
- **Feature-first clean architecture** (see AGENTS.md §C2). Each feature: `data / domain / presentation`.
- **Riverpod:** `AsyncNotifier` for async state; `ref.watch` in build, `ref.read` in callbacks; `select` to limit rebuilds; family providers for per-id data; global `selectedChildProvider` for guardians.
- **Routing:** go_router with typed routes, redirect guard (auth + role + force-update + maintenance), nested shells per role (bottom nav).
- **Networking:** Dio with interceptors — auth header, single-flight refresh on 401, retry with backoff for idempotent GETs, `X-App-Version`, error mapping to `Failure`; redact logs.
- **Models:** `freezed` + `json_serializable`; DTO ↔ entity mappers; no DTOs in UI.
- **UI:** Material 3 theme from tokens; reusable widgets (`AppScaffold`, `StatusChip`, `EmptyState`, `ErrorRetry`, `PagedListView`); Bangla font bundled; test text scale 1.3.
- **Forms:** validate locally, map server errors to fields.
- **l10n:** ARB `app_bn.arb` / `app_en.arb`; locale persisted; Bangla digits via `intl` `NumberFormat` with locale `bn`.
- **Flavors:** dev/staging/prod with distinct app IDs, base URLs, Firebase configs.
- **Platform config:** list each manifest/Info.plist/Gradle change in the Phase 1 report. Android minSdk/targetSdk decisions go in `DECISIONS.md`.
- **Testing:** unit (use cases, mappers), provider tests with `ProviderContainer` overrides, widget tests, goldens for key screens, `integration_test` for login → home.

### Rules
- No business logic in widgets.
- Every async screen: loading / data / empty / error / offline states.
- Never block UI thread with heavy parsing (use `compute`).
- Always check `context.mounted` after awaits.
- Dispose controllers; avoid memory leaks.

---
