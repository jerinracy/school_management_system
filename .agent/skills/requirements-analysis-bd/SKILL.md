---
name: requirements-analysis-bd
description: Use when a task touches Bangladeshi school domain rules — grading, exams, fees, admission, holidays, languages, mobile payments, SMS, MPO/EIIN, board exams. Prevents wrong local assumptions.
---

# requirements-analysis-bd

### Domain facts to apply (confirm with user if the school differs)
- **Grading (GPA 5.0, typical school scale):** 80–100 A+ (5.00), 70–79 A (4.00), 60–69 A- (3.50), 50–59 B (3.00), 40–49 C (2.00), 33–39 D (1.00), 0–32 F (0.00). **Make this configurable per institution**; never hard-code.
- Final GPA fails if any compulsory subject is F; **4th subject**: GPA above 2.00 is added to total points and divided by (subjects − 1) — implement as configurable rule, document in `DECISIONS.md`.
- Bangla/English have **1st & 2nd paper** → combined pass rule (configurable: separate pass or combined).
- Marks split: creative (CQ), MCQ, practical — each with its own pass mark.
- Sessions: January–December typical; exams: class test, half-yearly, annual, pre-test, test, model test.
- Groups from Class 9: Science / Commerce / Humanities(Arts).
- Weekend: Friday (and often Saturday) — configurable; holidays include Eid, Puja, Victory Day, Independence Day, Pohela Boishakh, etc. — editable calendar.
- Identifiers: **EIIN** (school), birth registration number (student), NID (guardian), roll number per class-section-session.
- Payments: bKash, Nagad, Rocket, SSLCommerz, aamarPay — always webhook/IPN-verified, idempotent.
- SMS: local gateways (masking vs non-masking); Bangla Unicode SMS = 70 chars/segment — compute cost correctly.
- Phone format: `01XXXXXXXXX` ↔ `+8801XXXXXXXXX` normalisation.
- Language: Bangla + English, Bangla numerals (০–৯) in print/UI where configured, Bangla PDF requires proper font embedding (Noto Sans Bengali / SolaimanLipi) and shaping (HarfBuzz-based).

### Rules
- If a rule is school-specific → make it a **configuration**, not code.
- Record every assumption in the Phase 1 report under "Assumptions".

---
