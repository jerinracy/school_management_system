---
name: code-review-self-check
description: Use at the end of Phase 2 before reporting. Self-review the diff against a checklist to catch bugs, leaks, and scope creep.
---

# code-review-self-check

### Checklist
- [ ] Diff contains only approved files/changes
- [ ] No tenant/permission leak (every query scoped, every endpoint guarded)
- [ ] No N+1, no unbounded queries
- [ ] No secrets / PII in code, logs, fixtures
- [ ] Migrations safe, reversible, named clearly
- [ ] Error paths and empty states handled
- [ ] Strings externalised (bn/en)
- [ ] Types strict (no `any` / no `dynamic` without reason)
- [ ] Tests cover happy + failure + permission
- [ ] Docs, OpenAPI, CHANGELOG updated

---
