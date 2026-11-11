---
name: system-design
description: Use in Phase 1 whenever a task introduces a new module, model, integration, or cross-cutting behavior. Produces a small design before code.
---

# system-design

### Procedure
1. Identify entities, relationships, and ownership (tenant/branch scoping).
2. Define invariants and state machines (e.g. Admission: draft → submitted → shortlisted → admitted/rejected).
3. Decide sync vs async work; identify idempotency keys.
4. Define permissions matrix: role × action.
5. Define events (e.g. `attendance.recorded`, `payment.confirmed`) and who consumes them.
6. Define failure modes (gateway timeout, device offline, duplicate punch) and handling.
7. Define data volume/indexing assumptions (e.g. attendance logs: millions of rows → partition/index plan).
8. Document: ER sketch (text), endpoint list, permissions matrix, state diagram.

### Output
Add a short ADR to `docs/DECISIONS.md` for any non-obvious choice.

---
