---
name: confirm-and-report
description: Use at the START of every task (to post an implementation plan and wait for approval) and at the END (to post a completion report). Mandatory for any change to code, config, schema, or dependencies.
---

# confirm-and-report

### Procedure
1. **Before touching any file**, gather: task prompt, affected modules, existing code, current migrations/contract.
2. Produce the **Implementation Report** exactly in the format defined in `AGENTS.md §A2 Phase 1`.
3. Fill the **What will change** table by actually inspecting the repo (list real paths, not guesses).
4. For backend tasks, fill **Database/Migration impact** by:
   - listing every model/field added, altered, removed
   - stating nullability/defaults, indexes, constraints
   - stating whether data backfill is needed and how
   - stating reversibility and rollback
   - stating the effect on existing rows and locking risk
5. State **API/Contract impact** and which clients (dashboard, Flutter) need regeneration.
6. End with: `Reply "approved" to proceed, or tell me what to change.` Then **stop**.
7. After implementation, produce the **Completion Report** with real command output.

### Rules
- Never merge Phase 1 and Phase 2 in the same message.
- If you discover new scope mid-implementation → stop → post an **Amendment Report** (what changed vs. plan, why, impact) → wait.
- "Looks fine" or silence ≠ approval.

### Self-check before posting a plan
- [ ] Every acceptance criterion maps to a bullet
- [ ] Every file in the table has a reason
- [ ] Migration effect explained in plain language
- [ ] Risks include permissions and data privacy
- [ ] Test plan is concrete (file names/commands)

---
