# 🎓 Bidyapith — Multi-Tenant School Management System (Bangladesh)

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.15-red?style=for-the-badge)](https://www.django-rest-framework.org/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![OpenAPI 3.0](https://img.shields.io/badge/OpenAPI-3.0_drf--spectacular-85EA2D?style=for-the-badge&logo=openapi-initiative&logoColor=black)](https://spec.openapis.org/)

---

## 📌 Overview

**Bidyapith** is an enterprise-grade, multi-tenant School Management System (SMS) engineered from the ground up for Bangladeshi educational institutions — covering Primary Schools, High Schools, Colleges (Higher Secondary), Madrasas, and English Medium/Version institutions.

The platform provides a unified administration experience, powering academic administration, multi-device biometric attendance, automated fee collections with Bangladeshi mobile financial services, NCTB GPA 5.0 examination tabulation, human resources & payroll, and automated parent communication.

---

## 🛠️ Technology Stack

```mermaid
graph TD
    subgraph Frontend ["Frontend Dashboard (Vite + React 18 SPA)"]
        UI["React 18 • TypeScript • Tailwind CSS"]
        State["TanStack Query v5 • Zustand"]
        Forms["React Hook Form • Zod Validation"]
        i18n["i18next (English & Bangla)"]
    end

    subgraph Backend ["Backend API Gateway (Django 5.1 + DRF)"]
        API["Django REST Framework • drf-spectacular"]
        Auth["SimpleJWT • OTP Challenge • RBAC"]
        ViteBridge["django-vite (SPA Shell Hosting)"]
        Services["Service Layer (Business Logic & Audit)"]
    end

    subgraph Async ["Async & Scheduled Task Workers"]
        Celery["Celery 5.4 Worker"]
        Beat["Celery Beat (Database Scheduler)"]
    end

    subgraph Storage ["Data Persistence & Cache"]
        PG[("PostgreSQL 16 (Tenant-Isolated Data)")]
        Redis[("Redis 7 (Cache, Broker & Locks)")]
    end

    UI -->|JSON REST API| API
    ViteBridge -.->|Serves Bundled SPA| UI
    API --> Services
    Services --> PG
    Services --> Redis
    Services -->|Dispatches Async Jobs| Celery
    Beat -->|Enqueues Crons| Celery
    Celery --> PG
```

### Backend & API
- **Language & Framework:** Python 3.12, Django 5.1.x, Django REST Framework 3.15.x
- **API Specification:** OpenAPI 3.0 with `drf-spectacular` & automated schema export
- **Authentication & Security:** SimpleJWT (Access/Refresh Tokens), Argon2 password hashing, Phone OTP verification, Role-Based Access Control (RBAC) with granular model permissions
- **Asynchronous Workers:** Celery 5.4, Celery Beat with `django-celery-beat` database scheduler, `django-celery-results`

### Frontend Dashboard
- **Build System & Framework:** Vite 6, React 18, TypeScript (Strict Mode)
- **Styling & UI Components:** Tailwind CSS, Radix UI primitives, Lucide React icons, Sonner toast notifications
- **State Management & Fetching:** TanStack Query v5 (server-state cache), Zustand (client UI state)
- **Forms & Validation:** React Hook Form + Zod schema validation
- **Internationalization:** `i18next` with complete English & Bengali (`bn`) localization and Bengali numerals (`toLocaleDigits`)
- **API Typing:** `openapi-typescript` auto-generated from backend schema contract

### Database & DevOps
- **Relational Database:** PostgreSQL 16 (Multi-tenant schema with `institution_id` discriminator column)
- **In-Memory Cache & Broker:** Redis 7 (Session caching, rate limiting, Celery broker)
- **Containerization:** Docker & Docker Compose
- **Web Server & Assets:** Gunicorn WSGI server, WhiteNoise static file serving, `django-vite` asset manifest bridge

---

## 🌟 Key Features & Modules

### 1. 🏢 Multi-Tenancy & Institutional Hierarchy
- **Tenant Isolation:** Every tenant entity inherits from `TenantOwnedModel` with strict tenant query filtering enforced at the base ORM layer.
- **Campuses & Branches:** Full support for multi-branch institutions (Main Campus, Secondary Branches).
- **Shift Management:** Configurable Morning and Day shifts with distinct start/end times and late arrival grace windows.
- **Academic Sessions & Terms:** Multi-year session tracking (e.g., Session 2026), 1st Term, 2nd Term, Annual Examination terms.
- **Institutional Configuration:** Education Board mapping (Dhaka, Chittagong, Rajshahi, Madrasa, etc.), EIIN numbers, MPO status, custom weekend configurations (Friday/Saturday).

### 2. 📚 Academic Lifecycle & Routine Builder
- **Curriculum & Classes:** Class levels (Play to Class 12 / Alim), Sections, Subject management (Compulsory, Elective, 4th Subject).
- **Interactive Routine Builder:** Visual timetable matrix builder with automatic period-teacher clash prevention.
- **Dedicated Section Supervisor:** Assign designated **Class Teachers** to sections with unique session validation; Class Teachers oversee daily attendance, leave approvals, and student welfare.
- **Student Enrollment:** Roll number allocation, shift assignments, and session promotion history.

### 3. 🕒 Biometric Attendance Engine
- **Hardware Integration:** Vendor-agnostic biometric adapter architecture supporting ZKTeco, Hikvision, Realtime, and ADMS push protocols over TCP/HTTP.
- **Intelligent Punch Parsing:** Automatic calculation of Present, Late, Half-Day, and Absent statuses based on institutional shift rules.
- **Teacher Attendance Taking:** Section supervisors can submit and override daily student roll calls.
- **Student Leave Requests:** Parent/student leave applications with document attachments and Class Teacher approval workflows.
- **Automated Alerts:** Dispatches instant SMS / Push notifications to parents when a child is late or absent.

### 4. 📝 NCTB GPA 5.0 Examination & Results
- **Standard NCTB Grading:** Automatic grade point computation (A+ 5.0, A 4.0, A- 3.5, B 3.0, C 2.0, D 1.0, F 0.0).
- **Multi-Part Assessments:** Continuous Assessment (CA), Creative Question (CQ), Multiple Choice (MCQ), and Practical components.
- **Bangladeshi Exam Rules:** Combined paper passing logic (e.g., Bangla 1st + 2nd, English 1st + 2nd) and 4th subject bonus points (points above 2.0 added to total GPA).
- **Reports & Broadsheets:** Generation of Tabulation Broadsheets and printable PDF Progress Report Cards with institution letterhead.

### 5. 💳 Fees, Invoicing & Mobile Financial Services
- **Flexible Fee Structures:** Tuition fees, admission charges, exam fees, session fees, laboratory fees, and transport levies.
- **Automated Billing:** Bulk monthly student invoice generation with configurable due dates, waivers, and late fine calculation.
- **MFS Gateway Integrations:** Native support for Bangladeshi payment channels:
  - **bKash** (Direct Checkout & Tokenized API)
  - **Nagad** (PGW API)
  - **Rocket** / **SSLCommerz** (Aggregated Gateway)
  - **Bank Challan / Cash Counter** receipts
- **Accounting Ledger:** Double-entry journal vouchers, fee collection tracking, and automated reconciliation.

### 6. 👥 Staff, HR & Biometric Payroll
- **Staff Directory:** Comprehensive employee records for Teachers, Administrative Staff, Drivers, and Support Personnel.
- **MPO Tracking:** MPO Index number, National ID (NID), Tax Identification Number (TIN), educational qualifications.
- **Attendance-Linked Payroll:** Automatic salary calculation with basic pay, allowances (house rent, medical), and deductions (late penalties, unpaid leaves).
- **Payslips:** Printable salary slips and disbursement ledger.

### 7. 📲 Communications Suite
- **Bangla Unicode SMS Gateway:** Multi-provider SMS integration (Teletalk, Greenweb, SSL Wireless, Alpha Net) with sender ID masking and DLR logging.
- **Notice Board:** Digital notices with target audiences (All, Students, Guardians, Teachers).
- **Push Notifications:** Firebase Cloud Messaging (FCM) integration for real-time mobile app alerts.

---

## 📁 Project Directory Structure

```text
├── apps/                        # Django modular backend applications (22 apps)
│   ├── academics/               # Classes, sections, subjects, routine builder, class teacher
│   ├── accounting/              # Double-entry ledger, vouchers, financial accounts
│   ├── accounts/                # Custom User model, SimpleJWT, OTP, RBAC permissions
│   ├── admissions/              # Online circulars, applicant registration, merit lists
│   ├── attendance/              # Roll call, raw punches, shift policies, leave requests
│   ├── audit/                   # Audit logging and sensitive state-change tracking
│   ├── communications/          # SMS gateway, notice board, FCM push alerts
│   ├── core/                    # BaseModel, TenantOwnedModel, soft-delete, BD utils
│   ├── devices/                 # Biometric terminal telemetry, ADMS protocols, sync
│   ├── events/                  # Institutional calendar, sports, annual functions
│   ├── exams/                   # Exam schedules, terms, grade profiles, mark sheets
│   ├── fees/                    # Fee heads, fee structures, student invoices, waivers
│   ├── guardians/               # Guardian profiles, student linkages, emergency contacts
│   ├── homework/                # Assignments, teacher submissions, file attachments
│   ├── hostel/                  # Dormitories, rooms, bed allocations, hostel fees
│   ├── institutions/            # Multi-tenant root, branches, shifts, academic sessions
│   ├── library/                 # Book catalogue, ISBN, lending, overdue fines
│   ├── payroll/                 # Salary structures, allowances, attendance deductions
│   ├── reports/                 # Executive dashboard KPIs, attendance rates, analytics
│   ├── results/                 # NCTB GPA 5.0 engine, tabulation sheets, report cards
│   ├── staff/                   # Employee directory, designations, MPO index
│   ├── students/                # Student directory, enrollments, roll numbers
│   └── transport/               # Fleet management, route stops, vehicle tracking
├── config/                      # Django project configuration
│   ├── settings/                # base.py, dev.py, prod.py, test.py
│   ├── celery.py                # Celery worker & scheduler setup
│   └── urls.py                  # Root URL router & OpenAPI schema endpoints
├── frontend/                    # Vite + React 18 SPA (Admin Dashboard)
│   ├── src/
│   │   ├── components/          # Reusable UI components (shadcn/ui & Radix)
│   │   ├── features/            # Feature-first modular UI:
│   │   │   ├── academics/       # Routine builder & class management
│   │   │   ├── attendance/      # Attendance roll call & leave requests
│   │   │   ├── dashboard/       # Executive KPI cards & system overview
│   │   │   ├── fees/            # Invoices & billing tables
│   │   │   ├── results/         # GPA calculation & grade cards
│   │   │   ├── staff/           # Staff directory & employee creation
│   │   │   └── students/        # Student directory & profile views
│   │   ├── i18n/                # Localization dictionary (en.json & bn.json)
│   │   ├── lib/                 # Formatting, Bengali numerals, theme utilities
│   │   └── types/               # TypeScript interfaces & auto-generated API types
├── docs/                        # Architecture decisions (DECISIONS.md), tasks, plan
├── schema/                      # OpenAPI 3.0 schema contract (schema.yml)
├── docker-compose.yml           # Multi-container orchestration (DB, Redis, API, Celery)
├── Dockerfile                   # Production-ready Python 3.12 container specification
├── Makefile                     # Developer convenience shortcut commands
├── pyproject.toml               # Tool configuration (Ruff, Black, Mypy, Pytest)
└── requirements.txt             # Production Python dependencies
```

---

## 🚀 Getting Started & Installation

### Prerequisites
- **Python:** 3.12+
- **Node.js:** 20.x or 22.x LTS (with `npm`)
- **PostgreSQL:** 16+
- **Redis:** 7+
- **Docker & Docker Compose** (Optional, for containerized run)

---

### Option 1: Native Local Setup (Recommended for Development)

#### 1. Clone the Repository
```bash
git clone https://github.com/your-org/school-management-system.git
cd "school-management-system"
```

#### 2. Backend Setup
Create a Python virtual environment and install dependencies:
```bash
python3.12 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure your PostgreSQL database credentials and Redis URLs are configured:
```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=your-dev-secret-key-1234567890abcdef
DATABASE_URL=postgres://sms_user:sms_password@localhost:5432/sms_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
```

#### 4. Run Migrations & Seed Initial Data
```bash
# Apply database migrations
python manage.py migrate

# Seed demo Bangladeshi institution (Dhaka Model High School & College, shifts, terms, holidays)
python manage.py seed_demo_institution

# Create administrative superuser
python manage.py createsuperuser
```

#### 5. Start Backend Services
In separate terminal windows:
```bash
# Terminal A: Start Django API Server
python manage.py runserver 0.0.0.0:8000

# Terminal B: Start Celery Worker
celery -A config worker -l info

# Terminal C: Start Celery Beat Scheduler
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

#### 6. Frontend Dashboard Setup
In a new terminal window:
```bash
cd frontend
npm install

# Start Vite React development server (hot reload enabled)
npm run dev
```

The frontend will run at **`http://localhost:5173`** and the Django backend at **`http://localhost:8000`**.

---

### Option 2: Docker Compose Setup

Run the entire platform (PostgreSQL, Redis, Django API, Celery Worker, and Celery Beat) in a single command:

```bash
docker compose up --build
```

- **Django Application:** `http://localhost:8000`
- **PostgreSQL Port:** `5432`
- **Redis Port:** `6379`

To apply migrations and seed demo data inside the container:
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo_institution
docker compose exec backend python manage.py createsuperuser
```

---

## ⚡ Useful Makefile Commands

A unified `Makefile` is provided for rapid execution:

| Command | Action |
|---|---|
| `make run` | Starts the Django development server on port 8000 |
| `make migrate` | Applies all pending database migrations |
| `make makemigrations` | Generates new migration files from model changes |
| `make test` | Executes backend test suite with Pytest |
| `make lint` | Checks code formatting and syntax with Ruff & Black |
| `make format` | Automatically formats Python code with Black & Ruff |
| `make typecheck` | Runs Mypy static type analysis across all apps |
| `make schema` | Regenerates and validates the OpenAPI schema file |
| `make fe-install` | Installs frontend NPM packages |
| `make fe-dev` | Starts the Vite React dashboard development server |
| `make fe-build` | Builds production-ready frontend bundle |
| `make fe-typecheck` | Executes TypeScript type checking (`tsc --noEmit`) |
| `make fe-test` | Runs frontend unit and integration tests with Vitest |
| `make fe-gen-api` | Auto-generates TypeScript API client types from OpenAPI schema |
| `make docker-up` | Launches full multi-container stack via Docker Compose |

---

## 📖 API Documentation & Contract-First Design

The backend enforces a contract-first architecture powered by `drf-spectacular`.

- **Interactive Swagger UI:** [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)
- **ReDoc Viewer:** [http://localhost:8000/api/schema/redoc/](http://localhost:8000/api/schema/redoc/)
- **OpenAPI Schema:** Exported to [schema/schema.yml](file:///home/sifat/Desktop/School Management System/schema/schema.yml)

### Synchronizing Schema with Frontend
Whenever backend endpoints, serializers, or query parameters are updated:
```bash
python manage.py spectacular --file schema/schema.yml --validate
cd frontend && npm run gen:api
```
This updates [frontend/src/types/api.ts](file:///home/sifat/Desktop/School Management System/frontend/src/types/api.ts) with zero hand-written types.

---

## 🔒 Security & Privacy Standards

- **Tenant Isolation:** Enforced at database and ORM query level. Cross-tenant data leakage is prevented via strict queryset scoping.
- **Biometric Data Safety:** In compliance with privacy standards, raw biometric face/fingerprint images are **never** stored. Only device-generated encrypted templates and punch logs are processed.
- **Child & Guardian Data Protection:** Guardian National IDs (NID) and phone numbers are masked in non-administrative logs.
- **Financial Idempotency:** Fee payments and wallet callback handlers wrap ledger updates in `transaction.atomic` with idempotency verification keys.

---

## 🇧🇩 Bangladesh Localization Details

| Feature | Standard Configuration |
|---|---|
| **Timezone** | `Asia/Dhaka` (UTC+6) with local device punch timestamp resolution |
| **Currency** | Bangladeshi Taka (`BDT` / `৳`) formatted with `Intl.NumberFormat` |
| **Bilingual UI** | English and Bengali with instant runtime toggle and offline persistence |
| **Numerals** | Support for Bengali digits (`০, ১, ২, ৩, ৪, ৫, ৬, ৭, ৮, ৯`) via `toLocaleDigits` |
| **Weekend Policy** | Configurable Friday & Saturday institutional holidays |
| **Grading System** | Official NCTB GPA 5.0 scale with 4th subject and combined paper arithmetic |
| **Phone Format** | Validation for `+8801XXXXXXXXX` across all telecom operators (Grameenphone, Banglalink, Robi, Airtel, Teletalk) |

---

## 📄 License & Contribution

This project is licensed under the **MIT License**.

Developed for modern Bangladeshi schools, colleges, and madrasas. For questions, feature requests, or deployment support, please open an issue in the repository.
