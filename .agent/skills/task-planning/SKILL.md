---
name: task-planning
description: Use when starting a task or when a task looks too large. Breaks work into small verifiable steps, orders them by dependency, and identifies risks before coding.
---

# task-planning

### Procedure
1. Restate the goal in one sentence and list explicit **non-goals**.
2. Identify dependencies on earlier tasks (check `docs/TASKS.md`). If a dependency is not DONE → flag BLOCKED.
3. Decompose into steps of ≤ ~1–2 hours each; each step must have a verifiable outcome.
4. Order: models/contract → services → API → tests → UI/integration → docs.
5. Identify the riskiest assumption and validate it first (spike if needed).
6. Estimate file count; if > 25 files, propose splitting into sub-tasks (`Task 14a`, `14b`).
7. Write the plan to `docs/PLAN.md` (module section) only after approval.

### Output template
```
Goal / Non-goals
Dependencies (DONE / BLOCKED)
Steps (numbered, each with "done when…")
Risks & mitigations
Open questions
```

---
