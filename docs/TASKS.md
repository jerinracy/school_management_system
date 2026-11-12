# Backend Tasks Tracker — School Management System

Legend:
- `TODO`: Not started
- `IN-PROGRESS`: Active work
- `DONE`: Completed, tested, verified, docs updated
- `BLOCKED`: Awaiting dependency

| Task ID | Task Name | Status | Dependencies | Completed Date |
|---|---|---|---|---|
| **Task 01** | Project Setup & Foundations | DONE | None | 2026-11-11 |
| **Task 02** | Institution, Branch, Shift, Academic Session | DONE | Task 01 | 2026-11-11 |
| **Task 03** | Auth, Users, Roles, Permissions, OTP, Sessions | DONE | Task 01, Task 02 | 2026-11-11 |
| **Task 04** | Academic Structure (Class, Section, Group, Subject, Routine) | DONE | Task 02, Task 03 | 2026-11-11 |
| **Task 05** | Admission (Online Application, Test, Merit, Lottery) | DONE | Task 04 | 2026-11-11 |
| **Task 06** | Student Lifecycle (Profile, Enrollment, Documents) | DONE | Task 04, Task 05 | 2026-11-11 |
| **Task 07** | Guardian Portal & Student-Guardian Relationship | DONE | Task 03, Task 06 | 2026-11-11 |
| **Task 08** | Staff & HR Management (Teachers, Employees, Designations) | DONE | Task 02, Task 03 | 2026-11-11 |
| **Task 09** | Biometric Device Management & Raw Punch Intake | DONE | Task 01, Task 08 | 2026-11-11 |
| **Task 10** | Attendance Engine (Daily Processing, Shifts, Leaves) | DONE | Task 06, Task 08, Task 09 | 2026-11-11 |
| **Task 11** | Exam Setup & Mark Entry | DONE | Task 04 | 2026-11-11 |
| **Task 12** | Grading Engine (GPA 5.0, BD National Curriculum) | DONE | Task 11 | 2026-11-11 |
| **Task 13** | Report Card Generation & Tabulation Sheet | DONE | Task 12 | 2026-11-11 |
| **Task 14** | Fee Structure & Invoice Generation | DONE | Task 06 | 2026-11-11 |
| **Task 15** | Payment Collection & Gateways (bKash, Nagad, SSLCommerz) | DONE | Task 14 | 2026-11-12 |
| **Task 16** | SMS Gateway Integration & Communication Suite | DONE | Task 03, Task 07 | 2026-11-12 |
| **Task 17** | Basic Accounting & Cashbook | TODO | Task 15 | - |
| **Task 18** | Payroll Management | TODO | Task 08, Task 10, Task 17 | - |
| **Task 19** | Homework & Assignment Management | TODO | Task 04, Task 06 | - |
| **Task 20** | Library Management | TODO | Task 06, Task 08 | - |
| **Task 21** | Transport Management | TODO | Task 06 | - |
| **Task 22** | Hostel Management | TODO | Task 06 | - |
| **Task 23** | Notice Board & Event Calendar | TODO | Task 02, Task 16 | - |
| **Task 24** | Audit Logging & Activity Tracking | TODO | Task 03 | - |
| **Task 25** | Reporting Engine & Data Exports | TODO | Task 06, Task 10, Task 13, Task 15 | - |
| **Task 26** | Hardening, Backup & Production Readiness | TODO | All Tasks | - |
