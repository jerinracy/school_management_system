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
| **Task 17** | Basic Accounting & Cashbook | DONE | Task 15 | 2026-11-12 |
| **Task 18** | Payroll Management | DONE | Task 08, Task 10, Task 17 | 2026-11-12 |
| **Task 19** | Homework & Assignment Management | DONE | Task 04, Task 06 | 2026-11-12 |
| **Task 20** | Library Management | DONE | Task 06, Task 08 | 2026-11-12 |
| **Task 21** | Transport Management | DONE | Task 06 | 2026-11-12 |
| **Task 22** | Hostel Management | DONE | Task 06 | 2026-11-12 |
| **Task 23** | Notice Board & Event Calendar | DONE | Task 02, Task 16 | 2026-11-12 |
| **Task 24** | Audit Logging & Activity Tracking | DONE | Task 03 | 2026-11-12 |
| **Task 25** | Reporting Engine & Data Exports | DONE | Task 06, Task 10, Task 13, Task 15 | 2026-11-12 |
| **Task 26** | Hardening, Backup & Production Readiness | TODO | All Tasks | - |
| **Task 27** | Academic Session Lifecycle, Session-Scoped Communications & Soft-Delete Mixin | DONE | Task 02, Task 04, Task 16 | 2026-11-23 |
| **Task 28** | Dynamic Session Scoping for Students/Guardians, Copy Wizard Rollover Fix & Mobile Option A Sync | DONE | Task 06, Task 07, Task 27 | 2026-11-23 |
| **Task 29** | Active Session Scoping for MyChildren, Mobile Not-Enrolled Warning Banner & Navigation De-duplication | DONE | Task 07, Task 28 | 2026-11-23 |
| **Task 30** | Unenrolled Session Access Lock & Full Routine/Teacher/Chat Isolation | DONE | Task 07, Task 28, Task 29 | 2026-11-23 |

---

# Frontend Tasks Tracker — Admin Dashboard (`frontend/`)

| Task ID | Task Name | Status | Dependencies | Completed Date |
|---|---|---|---|---|
| **Task F01** | Vite + React + django-vite Setup | DONE | Backend Task 01 | 2026-11-12 |
| **Task F02** | Design System, Layout & Theming | DONE | Task F01 | 2026-11-12 |
| **Task F03** | Auth, API Client & Permissions | DONE | Backend Task 03 | 2026-11-14 |
| **Task F04** | Institution Setup & Academic Structure Screens | DONE | Task F03, Backend Task 02, Task 04 | 2026-11-14 |
| **Task F05** | Full-Page Institutional Login & Dynamic Branding System | DONE | Task F03, Task F04 | 2026-11-14 |
| **Task F06** | Student Lifecycle & Information System (SIS) & Admissions Management | DONE | Task F04, Task F05, Backend Task 05, Task 06, Task 07 | 2026-11-14 |
| **Task F07** | Staff & HR Management Dashboard (Roster, Onboarding, 360° Profile, Leaves & CR80 ID Cards) | DONE | Task F06, Backend Task 08 | 2026-11-14 |
| **Task F08** | Biometric Devices & Attendance Engine Dashboard (Hardware Terminals, Punch Logs, Corrections, Period Register, Policies) | DONE | Task F07, Backend Task 09 | 2026-11-15 |
| **Task F09** | Examinations, Continuous Assessment & GPA 5.0 Result Processing Dashboard (Lifecycle, Mark Entry, Hall Passes, Broadsheet Tabulation, Report Cards, Grading Scales) | DONE | Task F08, Backend Task 10, Task 11 | 2026-11-15 |
| **Task F10** | Fees, Billing & Financial Accounting Dashboard (Fee Structures, Student Invoices, Waivers, Counter POS Collection, 3-Part Money Receipts, Due Defaulters, Day Book/Cashbook) | DONE | Task F09, Backend Task 14, Task 15, Task 17 | 2026-11-15 |
| **Task F11** | Staff Payroll Management Dashboard (Salary Structures, Biometric Attendance-linked Payslip Generation, Allowances, Deductions, Bank/Cash Disbursement, Salary Registers) | DONE | Task F07, Task F08, Task F10, Backend Task 18 | 2026-11-15 |
| **Task F12** | Communications & Notice Board Dashboard (Bulk Bangla Unicode SMS Campaigns, Dynamic Placeholders, SMS Gateway Balance/DLR Logs, Push Notifications, Notice Board & Academic Event Calendar) | DONE | Task F03, Task F04, Backend Task 16, Task 23 | 2026-11-15 |
| **Task F13** | Institutional Operations & Student Services Dashboard (Homework & Assignment Evaluation, Library Catalog & Circulation, Transport Fleet & Routes, Hostel Dorms & Allocation) | DONE | Task F04, Task F06, Backend Tasks 19, 20, 21, 22 | 2026-11-15 |
| **Task F14** | Enterprise Audit Logging, Dynamic Reporting Engine & CSV/Excel/PDF Exports | DONE | All Prior Tasks, Backend Tasks 24, 25 | 2026-11-15 |
| **Task F15** | OpenAPI Schema, Mobile API Contract & Brief Synchronization | DONE | All Prior Tasks | 2026-11-19 |
| **Task F16** | Mobile App & Portal Login Provisioning (Students, Guardians, Teachers) | DONE | Task 03, Task 06, Task 07, Task 08 | 2026-11-19 |
| **Task F17** | Edit, Update & Delete Lifecycle Management (Students, Teachers, Guardians, Staff) | DONE | Task F06, Task F07, Task F16 | 2026-11-19 |
| **Task F18** | Class Teacher Assignment & Supervision Integration in Routine Builder | DONE | Task F04, Task F08, Task F17 | 2026-11-19 |
| **Task F19** | Professional Operational Overview Dashboard Redesign (Headcount KPIs, Shifts, Faculty, Quick Actions, Compact Setup Banner) | DONE | Task F01, Task F14, Task F18 | 2026-11-22 |
| **Task F20** | Full Admin Dashboard Unslopping (Surface Gradients, Looping Animations, Tracking, Emoji Removal, Neutral Chrome) | DONE | Task F19 | 2026-11-22 |
| **Task F21** | Academic Session Management & Comprehensive Edit/Delete Modals (Sessions, Classes, Sections, Subjects, Offerings, Periods, Rooms) | DONE | Task F04, Task F17, Backend Task 27 | 2026-11-23 |
| **Task F22** | Academic Context Automatic Cache Invalidation, Copy Structure Wizard Redesign & Session Empty States | DONE | Task F06, Task F21, Backend Task 28 | 2026-11-23 |
