---
name: ui-ux-design
description: Use before building any screen (dashboard or Flutter). Produces a layout description, states, and interaction flow, and enforces consistent design language and accessibility.
---

# ui-ux-design

### Procedure
1. For each screen list: purpose, user role, primary action, data shown, filters, empty/loading/error/offline states.
2. Describe layout (wireframe in text), components used from the design system, responsive behaviour.
3. Define flows: happy path + 2 failure paths.
4. Bangla-specific: allow ~30% longer text, don't truncate meaningful Bangla words mid-conjunct, test Bangla digits, use Noto Sans Bengali.
5. Accessibility: contrast AA, tap targets ≥ 48dp (mobile), focus order, semantic labels, no colour-only meaning (attendance Present/Absent/Late needs icon + text).
6. Consistent patterns: list+filter+detail drawer (dashboard); card list + pull-to-refresh (mobile).
7. Destructive actions always confirm; show impact ("This will remove 32 students from Class 6-A").

### Design tokens (agree once in Task 02, then reuse)
Primary, secondary, success, warning, danger, neutral scale, radius, spacing scale (4/8), typography scale, elevation. Light + dark mode.

---
