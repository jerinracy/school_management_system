---
name: django-vite-integration
description: Use when wiring, debugging, or deploying the React SPA served via django-vite (dev server, manifest, static files, SPA routing, CSRF/CORS).
---

# django-vite-integration

### Setup facts
- `INSTALLED_APPS += ["django_vite"]`; `DJANGO_VITE = {"default": {"dev_mode": DEBUG, "manifest_path": BASE_DIR / "static/dashboard/.vite/manifest.json", ...}}` (verify the exact keys against the installed django-vite version).
- Template: `{% load django_vite %}` → `{% vite_hmr_client %}` + `{% vite_react_refresh %}` (dev) and `{% vite_asset 'src/main.tsx' %}`.
- `vite.config.ts`: `base` = static URL in prod, `build.manifest: true`, `build.outDir` into Django static dir, dev server `origin`/`strictPort`, proxy `/api` to Django in dev.
- Django serves SPA shell at `dashboard/` and `dashboard/<path:path>` (catch-all → same template) so React Router deep links work; `/api/`, `/admin/`, `/static/`, `/media/` must not be swallowed.
- Auth: prefer same-origin (cookie-based refresh + CSRF) since SPA is served by Django; if using Authorization header, keep access token in memory.
- Prod: `npm run build` → `collectstatic` → serve via WhiteNoise/Nginx with long cache for hashed files.

### Debug checklist
- Blank page → check `manifest.json` path & entry key; `dev_mode` flag; Vite server running & reachable (HMR WebSocket).
- 404 on deep link → catch-all URL missing or ordered after other routes.
- CSRF 403 → missing CSRF cookie/header or wrong `CSRF_TRUSTED_ORIGINS`.
- Stale assets → hashed filenames, clear browser/CDN cache.

---
