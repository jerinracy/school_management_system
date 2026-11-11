---
name: development-standards
description: Use during implementation (Phase 2) in any repo. Enforces small steps, clean code, naming, error handling, and security basics.
---

# development-standards

### Checklist
- Small functions, single responsibility, meaningful names (domain terms: `fee_head`, `academic_session`, `punch`).
- No dead code, no commented-out blocks, no TODO without a task reference.
- Handle errors explicitly; never swallow exceptions; user-facing messages are translatable.
- No secrets, no PII in logs.
- Validate at boundaries (API input, device payloads, webhook payloads) — verify signatures for gateway/device webhooks.
- Prefer composition and explicit dependencies over globals.
- Commit message format: `feat(attendance): add shift-based late rule` (Conventional Commits).
- Update docs as you go.

---
