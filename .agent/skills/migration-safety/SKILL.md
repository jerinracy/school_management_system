---
name: migration-safety
description: Use whenever a model change creates or alters a migration. Ensures migrations are safe, reversible, explained to the user, and do not harm existing data.
---

# migration-safety

### Procedure
1. Run `python manage.py makemigrations --dry-run -v 3` and read the output.
2. Classify each operation: **Safe** (add nullable column, add table, add index concurrently) / **Caution** (add NOT NULL w/ default, add unique, alter type) / **Dangerous** (drop column/table, rename, data loss).
3. For Caution/Dangerous: use multi-step pattern (add nullable → backfill in data migration → add constraint → remove old in a later release).
4. Check `sqlmigrate <app> <number>` and quote the key SQL in the report.
5. Confirm reversibility (`migrate <app> <previous>`); provide `RunPython` reverse functions.
6. Estimate impact on existing data: rows affected, lock duration, required downtime.
7. Postgres: use `AddIndexConcurrently` / `atomic = False` for big tables.
8. Never edit an applied migration; never squash without approval.
9. Run `makemigrations --check` in CI to catch missing migrations.
10. Test: migrate forward on a copy with sample data, then backward if reversible.

### Report block (copy into Phase 1)
```
Migration: apps/<app>/migrations/00NN_<name>.py
Operations: <list>
Classification: Safe | Caution | Dangerous
Existing data effect: <plain language>
Backfill: <none | description>
Locking/downtime: <none | estimate>
Reversible: yes/no — rollback: <command/steps>
```

---
