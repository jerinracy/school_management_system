---
name: debugging
description: Use whenever a test fails, an error appears, or behaviour differs from expectation. Enforces systematic root-cause analysis instead of trial-and-error edits.
---

# debugging

### Procedure (do not skip steps)
1. **Reproduce** — get the exact failing command/input; write a failing test if feasible.
2. **Read the error fully** — stack trace, SQL, HTTP status/body, Flutter exception + widget stack.
3. **Isolate** — bisect: which layer? (model → service → serializer → view → permission → URL → client). Narrow by logging/`pdb`/breakpoints.
4. **Hypothesise** — write down 1–3 hypotheses ranked by likelihood; test the cheapest first.
5. **Root cause** — fix the cause, not the symptom. State it in one sentence.
6. **Fix minimally**, keep the failing test as a regression test.
7. **Verify** — run the broader suite; check for side effects.
8. **Report** — in the Completion Report: symptom, root cause, fix, regression test.

### Stack-specific toolbox
- **Django:** `python manage.py shell_plus`, `django-debug-toolbar`/`silk` for queries, `connection.queries`, `EXPLAIN ANALYZE`, `pytest -x --pdb`, Celery: `celery -A config inspect active`, check task retries/dead letters.
- **DRF:** check `permission_classes`, `get_queryset` tenant filter, serializer `.errors`, spectacular warnings.
- **Migrations:** `showmigrations`, `sqlmigrate`, conflicting leaf nodes → `makemigrations --merge` only after review.
- **Vite/React:** browser console + Network tab, React DevTools, TanStack Query Devtools, check CORS/CSRF/proxy, check `manifest.json` entry for django-vite.
- **Flutter:** `flutter doctor -v`, DevTools (widget inspector, network, performance), `debugPrint` with redaction, check `ref.watch` vs `ref.read`, async gaps (`mounted` checks), Gradle/Pod errors → read the first error, not the last.
- **Biometric devices:** capture raw payload, check timezone/clock drift, duplicate punches, device SN mapping, network/ADMS push logs.

### Anti-patterns (forbidden)
- Random edits until it works; disabling tests; broad `try/except: pass`; adding `sleep()` to "fix" races; changing applied migrations.

---
