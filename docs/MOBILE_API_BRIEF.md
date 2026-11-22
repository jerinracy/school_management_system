# Mobile API Brief — School Management System (Flutter Team)

> **Source of truth:** Backend codebase (`config/`, `apps/`) and OpenAPI schema (`schema/schema.yml`).
> **Note:** The prompt referred to `schema/openapi.yml`; in this repository the generated OpenAPI 3.0 schema lives at `schema/schema.yml` (regenerated via `python manage.py spectacular --file schema/schema.yml --validate`).

---

## 1. Base URL, API Version & Required Headers

### Base URL & Versioning
- **API Version:** `v1`
- **Base URL Pattern:** `https://<host>/api/v1/` (local dev: `http://127.0.0.1:8000/api/v1/`)
- **OpenAPI Schema Endpoints:**
  - Raw schema: `GET /api/schema/`
  - Swagger UI: `GET /api/docs/`
  - ReDoc: `GET /api/redoc/`
- **Health & Metrics:**
  - `GET /api/v1/health/` (no auth required)

### Required & Supported Headers

| Header | Required | Behavior in Backend | Notes |
|--------|----------|---------------------|-------|
| `Authorization` | Yes (except public/login/OTP endpoints) | `Bearer <access_token>` (`SIMPLE_JWT["AUTH_HEADER_TYPES"] = ("Bearer",)`) | Enforced by `JWTAuthentication`. |
| `Content-Type` | Yes for JSON/multipart | `application/json` (or `multipart/form-data` for file uploads) | Standard DRF parsers. |
| `Accept-Language` | Recommended | Handled by Django `LocaleMiddleware` (`LANGUAGE_CODE = "en"` default). | Send `bn` or `en`. Note: user profile also stores `language_preference` (`"bn"` default on `User`). |
| `X-App-Version` | **Not enforced yet (GAP)** | **Not read or checked by any backend middleware/view.** | See **Section 11 (GAPS)**. Note: `POST /api/v1/auth/login/` accepts `app_version` in the JSON body (not header) for `UserSession` tracking. |

---

## 2. Authentication Flows (Exact Implementation)

All auth endpoints live under `/api/v1/auth/`.

### 2.1 Password Login — `POST /api/v1/auth/login/`
- **Permission:** `AllowAny`
- **Lockout policy:** `5` failed attempts within `15` minutes locks the account (`HTTP 429` with code `ACCOUNT_LOCKED`).
- **Identifier:** Accepts username, phone (`+8801XXXXXXXXX`), or email in `identifier`.

**Request:**
```json
{
  "identifier": "+8801712345678",
  "password": "StrongPassword123!",
  "device_id": "flutter-device-uuid",
  "device_name": "Samsung Galaxy A54",
  "platform": "android",
  "app_version": "1.0.0",
  "fcm_token": "fcm-registration-token-optional"
}
```
(`device_id`, `device_name`, `platform`, `app_version`, `fcm_token` are optional; `platform` choices: `web`, `android`, `ios`, `other`.)

**Response (`200 OK` — Standard Success):**
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": "uuid",
    "username": "guardian_01",
    "full_name": "Rahim Uddin",
    "phone": "+8801712345678",
    "email": "rahim@example.com",
    "user_type": "guardian",
    "institution_id": "uuid-or-null",
    "roles": ["Guardian"],
    "must_change_password": false,
    "language_preference": "bn"
  }
}
```

**Response (`200 OK` — 2FA / TOTP Enabled):**
If `user.is_totp_enabled` is `true`, login does **not** issue tokens; it returns:
```json
{
  "code": "TOTP_REQUIRED",
  "message": "2FA verification required.",
  "user_id": "uuid"
}
```
> **IMPORTANT GAP:** There is currently **no `/api/v1/auth/totp/verify/` endpoint** in `apps/accounts/urls.py` to exchange `user_id` + TOTP code for JWT tokens. See **Section 11 (GAPS)**.

**Response (`429 Too Many Requests` — Account Locked):**
```json
{
  "code": "ACCOUNT_LOCKED",
  "message": "Account locked due to multiple failed attempts. Try again in 15 minutes.",
  "details": null
}
```

---

### 2.2 OTP Login — `POST /api/v1/auth/otp/request/` & `POST /api/v1/auth/otp/verify/`

#### Step 1: Request OTP (`POST /api/v1/auth/otp/request/`)
- **Permission:** `AllowAny`
- **Rate limit:** Max `3` OTP requests per phone per `5` minutes; OTP expires in `5` minutes.

**Request:**
```json
{
  "phone": "+8801712345678",
  "purpose": "login"
}
```
(`purpose` choices: `"login"`, `"password_reset"`, `"verify_phone"`; defaults to `"login"`.)

**Response (`200 OK`):**
```json
{
  "message": "If the phone number is registered, an OTP has been sent.",
  "expires_in": 300
}
```

#### Step 2: Verify OTP (`POST /api/v1/auth/otp/verify/`)
- **Permission:** `AllowAny`
- **Max wrong attempts:** `3` before OTP is invalidated.

**Request:**
```json
{
  "phone": "+8801712345678",
  "code": "123456",
  "purpose": "login",
  "device_id": "flutter-device-uuid",
  "platform": "android"
}
```

**Response (`200 OK`):**
Identical structure to Password Login (`{ "access", "refresh", "user": { ... } }`).

---

### 2.3 Token Refresh & Rotation — `POST /api/v1/auth/refresh/`
- **Permission:** `AllowAny` (uses `TokenRefreshView` from `rest_framework_simplejwt`)
- **Settings (`config/settings/base.py`):**
  - `ACCESS_TOKEN_LIFETIME`: `60 minutes`
  - `REFRESH_TOKEN_LIFETIME`: `7 days`
  - `ROTATE_REFRESH_TOKENS`: `True`
  - `BLACKLIST_AFTER_ROTATION`: `True`
- **Client rule:** Every refresh call returns a **new `access` AND a new `refresh`** token and blacklists the old `refresh` token. The Flutter app **must persist both** immediately in `flutter_secure_storage` and serialize concurrent refresh calls (mutex/lock in Dio interceptor) to avoid reusing a rotated/blacklisted refresh token.

**Request:**
```json
{
  "refresh": "<current_refresh_token>"
}
```

**Response (`200 OK`):**
```json
{
  "access": "<new_access_token>",
  "refresh": "<new_refresh_token>"
}
```

---

### 2.4 Logout & Session Revocation
- **Single-device logout:** `POST /api/v1/auth/logout/`
  - **Permission:** `IsAuthenticated`
  - **Request:** `{ "refresh": "<current_refresh_token>" }`
  - **Response (`200 OK`):** `{ "message": "Logged out successfully." }`
  - Blacklists the refresh token and marks matching active `UserSession` inactive.
- **Logout all devices:** `POST /api/v1/auth/logout-all/`
  - **Permission:** `IsAuthenticated`
  - **Request:** `{}` (empty body)
  - **Response (`200 OK`):** `{ "message": "All sessions terminated." }`
- **Session management:**
  - `GET /api/v1/auth/sessions/` — list active sessions
  - `POST /api/v1/auth/sessions/{id}/revoke/` — revoke a specific session

---

### 2.5 Force Password Change — `POST /api/v1/auth/password/change/`
- **Permission:** `IsAuthenticated`
- **Trigger:** When `login` or `otp/verify` returns `user.must_change_password === true` (typical for newly provisioned guardian/student/staff accounts), the Flutter app should route to a mandatory "Change Password" screen before entering the main shell.
- **Note:** Backend does **not** currently block other API endpoints when `must_change_password=True`; enforcement on mobile is client-driven based on `user.must_change_password`.

**Request:**
```json
{
  "old_password": "TempPassword123!",
  "new_password": "NewStrongPassword456!"
}
```
(`new_password` is validated against Django `AUTH_PASSWORD_VALIDATORS`.)

**Response (`200 OK`):**
```json
{
  "message": "Password updated successfully."
}
```
Backend sets `user.must_change_password = False`.

---

### 2.6 Current User Profile — `GET /api/v1/auth/me/` & `PATCH /api/v1/auth/me/`
- **GET Response:** Returns user fields plus `"permissions": [...]` (list of resolved permission codes from assigned `Role`s).
- **PATCH Request:** Allows updating profile preferences such as `language_preference` (`"bn"` or `"en"`).

---

## 3. Roles & Endpoint Access

`User.user_type` (`apps/accounts/models.py`) defines 13 user types:
`superadmin`, `admin`, `head_teacher`, `assistant_head`, `teacher`, `accountant`, `librarian`, `clerk`, `staff`, `student`, `guardian`, `driver`, `security`.

> **Permissions architecture note:** All endpoints require `IsAuthenticated` + `AdminSecurityPermission` by default, plus module-specific permission classes and `TenantScopedMixin` (all queries filtered by `request.user.institution`).

| Mobile Role | `user_type` | Accessible Endpoint Groups |
|-------------|-------------|----------------------------|
| **Guardian** | `guardian` | `auth/*`, `guardians/guardians/my-children/`, `guardians/pickups/` (authorized pickups + OTP), `attendance/daily/` & `attendance/events/`, `academics/routines/` & `academics/subjects/`, `results/exam-results/`, `results/report-cards/` (`download/`), `exams/routines/`, `fees/invoices/`, `fees/payments/` (`initiate-online/`, `verify/`), `fees/receipts/`, `communications/notices/`, `communications/chat/threads/`, `communications/device-tokens/`, `communications/preferences/me/`, `events/events/` (`rsvp/`), `events/notice-receipts/` (`mark-read/`), `events/calendar/`, `homework/assignments/`, `homework/submissions/`, `homework/download/`, `transport/live-locations/latest/`, `transport/boarding-events/`, `hostel/gate-passes/` |
| **Student** | `student` | `auth/*`, `attendance/daily/`, `academics/*` (read-only), `exams/routines/`, `exams/admit-cards/`, `results/exam-results/`, `results/report-cards/` (`download/`), `fees/invoices/` & `fees/payments/` (read/pay), `homework/assignments/` (`submit/`), `homework/materials/`, `homework/online-classes/`, `homework/quizzes/` (`start_attempt/`, `submit_attempt/`, `my_attempts/`), `homework/download/`, `communications/notices/`, `communications/device-tokens/`, `communications/preferences/me/`, `events/calendar/`, `library/books/` & `library/reservations/`, `hostel/gate-passes/` |
| **Teacher** | `teacher` | `auth/*`, `academics/*` (routines, subjects, classes, sections), `students/` (read), `attendance/daily/`, `attendance/periods/`, `attendance/mobile-checkin/` (`checkin/`), `staff/leave-requests/` & `staff/leave-balances/`, `homework/assignments/` (CRUD, `upload_attachment/`, `publish/`, `close/`, `submissions/`), `homework/submissions/{id}/grade/`, `homework/lesson-plans/`, `homework/syllabus-topics/`, `homework/materials/`, `homework/quizzes/`, `exams/mark-entries/` (`bulk_save/`, `export_template/`, `import_excel/`), `communications/notices/`, `communications/chat/threads/`, `communications/device-tokens/`, `communications/preferences/me/` |
| **Staff / Management** | `staff`, `admin`, `head_teacher`, `assistant_head`, `accountant`, `librarian`, `clerk` | All teacher/operations endpoints above, plus role-scoped management: `reports/kpi/` (`reports/`), `admissions/`, `fees/payments/counter/` (accountant/admin), `exams/mark-entries/lock/` & `unlock/`, `results/publications/` (`approve/`, `publish/`, `unpublish/`), `attendance/corrections/`, `payroll/`, `accounting/`, `library/`, `hostel/`, `audit/` (admin) |
| **Driver** | `driver` | `auth/*`, `transport/vehicles/`, `transport/routes/`, `transport/stops/`, `transport/assignments/`, `transport/trips/` (`start/`, `end/`), `transport/boarding-events/scan/`, `transport/gps/ping/` (`GpsPingView`), `communications/device-tokens/`, `communications/notices/`. *(See Section 11 GAP on driver-specific user linkage.)* |
| **Security** | `security` | `auth/*`, `guardians/pickups/` (`send-otp/`, `verify-otp/`), `hostel/gate-passes/` (gate exit/return verification), `hostel/visitors/`, `attendance/mobile-checkin/` (`checkin/`), `communications/device-tokens/`, `communications/notices/`. *(See Section 11 GAP on dedicated security gate-log endpoints.)* |

---

## 4. Ordered Endpoint Flows per Mobile Feature

### 4.1 App Startup & Session Bootstrap
1. `GET /api/v1/auth/me/` — hydrate user profile, `user_type`, `institution_id`, `permissions`, `language_preference`, `must_change_password`.
2. If `must_change_password == true` → route to `POST /api/v1/auth/password/change/`.
3. `POST /api/v1/communications/device-tokens/` — register/refresh FCM token.
4. `GET /api/v1/institutions/profile/` — fetch school branding (name EN/BN, logo, settings).

### 4.2 Guardian Home (Multi-Child Selector)
1. `GET /api/v1/guardians/guardians/my-children/` — returns linked wards (`id`, `student_id`, `name_en`, `name_bn`, `photo`, `relation`, `is_primary`, `can_pickup`, `student` enrollment summary). Store selected child ID in global Riverpod provider.
2. Parallel dashboard widgets for selected `student_id`:
   - `GET /api/v1/attendance/daily/?student=<student_id>`
   - `GET /api/v1/fees/invoices/?student=<student_id>&status=unpaid` (or `partial`)
   - `GET /api/v1/homework/assignments/?student=<student_id>`
   - `GET /api/v1/communications/notices/?is_pinned=true`
   - `GET /api/v1/events/calendar/`

### 4.3 Attendance (Guardian/Student View & Teacher Period Marking)
- **Guardian/Student view:**
  1. `GET /api/v1/attendance/daily/?student=<student_id>&date_after=<YYYY-MM-DD>&date_before=<YYYY-MM-DD>`
  2. `GET /api/v1/attendance/events/?student=<student_id>` (raw biometric/mobile punch logs)
- **Teacher / Staff period attendance:**
  1. `GET /api/v1/academics/routines/` (get today's assigned periods)
  2. `GET /api/v1/students/enrollments/?section=<section_id>&session=<session_id>` (student roster)
  3. `POST /api/v1/attendance/periods/` (submit period attendance)

### 4.4 Staff / Teacher Mobile GPS Check-In
1. `GET /api/v1/attendance/policies/` (optional: inspect active geofence policy)
2. `POST /api/v1/attendance/mobile-checkin/checkin/` with `{ "latitude": 23.8103, "longitude": 90.4125 }` (optional `accuracy_meters`, `selfie_image`, `device_info`, `timestamp`). Uses `PunchDirection.AUTO` for both check-in and check-out; returns `201 Created` when within geofence or `400 Bad Request` (`status: "rejected"`) when outside geofence.
3. `GET /api/v1/attendance/mobile-checkin/` to view check-in history

### 4.5 Exams & Results
- **Guardian / Student:**
  1. `GET /api/v1/exams/exams/`
  2. `GET /api/v1/exams/routines/?exam=<exam_id>`
  3. `GET /api/v1/exams/admit-cards/?student=<student_id>` → `GET /api/v1/exams/admit-cards/{id}/download_pdf/`
  4. `GET /api/v1/results/exam-results/?student=<student_id>&exam=<exam_id>`
  5. `GET /api/v1/results/report-cards/?exam_result=<exam_result_id>` → `GET /api/v1/results/report-cards/{id}/download/` (PDF)
  6. `GET /api/v1/results/student-results/?exam=<exam_id>&class_level=<class_id>&section=<section_id>` — batch/summary student exam results with position rankings (`class_position`, `section_position`), GPA, total marks, percentage, and pass/fail status.
- **Teacher Marks Entry:**
  1. `GET /api/v1/exams/exams/` → `GET /api/v1/exams/subjects/?exam=<exam_id>`
  2. `GET /api/v1/exams/mark-entries/?exam_subject=<exam_subject_id>`
  3. `POST /api/v1/exams/mark-entries/bulk_save/` with `{ "exam_subject_id": "...", "entries": [...] }` (returns `200` or `207 Multi-Status` with per-row `errors`)

### 4.6 Fees & Online Payment Flow (bKash / Nagad / SSLCommerz / aamarPay)
1. `GET /api/v1/fees/invoices/?student=<student_id>` — list invoices and `balance_due`
2. `GET /api/v1/fees/invoices/{id}/` — invoice line items
3. `GET /api/v1/fees/student-waivers/?student=<student_id>` — list applied fee waivers and scholarships
4. `POST /api/v1/fees/payments/initiate-online/`
   - Body: `{ "invoice_id": "<uuid>", "payment_method": "bkash" | "nagad" | "sslcommerz" | "aamarpay", "success_url": "...", "fail_url": "...", "cancel_url": "..." }`
   - Response (`200 OK`): `{ "payment_id": "<uuid>", "gateway_url": "https://...", "transaction_id": "..." }`
5. Open `gateway_url` in Flutter WebView / in-app browser; intercept redirect to `success_url` / `fail_url` / `cancel_url`.
6. `POST /api/v1/fees/payments/verify/` — verify transaction with `{ "payment_id": "<uuid>", ...gateway_params }`.
7. `GET /api/v1/fees/receipts/?payment=<payment_id>` — fetch/download money receipt.

### 4.7 Notices & Events
1. `GET /api/v1/communications/notices/` (supports filtering/ordering, pinned notices first)
2. `POST /api/v1/events/notice-receipts/mark-read/` — mark notice as read
3. `GET /api/v1/events/events/` → `POST /api/v1/events/events/{id}/rsvp/`
4. `GET /api/v1/events/calendar/` — unified academic + holiday + event calendar

### 4.8 Chat (Guardian ↔ Teacher)
1. `GET /api/v1/communications/chat/threads/` — list threads (or `POST` to create/get thread)
2. `GET /api/v1/communications/chat/threads/{id}/messages/` — fetch thread messages (ordered by `created_at` ASC)
3. `POST /api/v1/communications/chat/threads/{id}/messages/` with `{ "content": "..." }` — send message (`201 Created`)
4. `POST /api/v1/communications/chat/threads/{id}/mark-read/` — mark unread messages from other user as read

### 4.9 Homework & Learning
- **Student / Guardian:**
  1. `GET /api/v1/homework/assignments/`
  2. `GET /api/v1/homework/assignments/{id}/` (attachments include signed download URLs)
  3. `GET /api/v1/homework/download/?token=<signed_token>` (download attachment)
  4. `POST /api/v1/homework/assignments/{id}/submit/` (`multipart/form-data` with `text_response`, `files`, optional `student` UUID for guardian)
  5. `GET /api/v1/homework/submissions/?homework=<id>`
- **Teacher:**
  1. `POST /api/v1/homework/assignments/` (draft) → `POST /api/v1/homework/assignments/{id}/upload_attachment/` → `POST /api/v1/homework/assignments/{id}/publish/`
  2. `GET /api/v1/homework/assignments/{id}/submissions/`
  3. `POST /api/v1/homework/submissions/{id}/grade/`

### 4.10 FCM Device-Token Registration & Preferences
1. `POST /api/v1/communications/device-tokens/`
   - Body: `{ "token": "<fcm_token>", "device_id": "<device_uuid>", "platform": "android" | "ios" }`
   - Upserts (`update_or_create`) by `(institution, user, token)` and sets `is_active = true`.
2. `DELETE /api/v1/communications/device-tokens/{id}/` (on logout or token invalidation)
3. `GET /api/v1/communications/preferences/me/` & `PATCH /api/v1/communications/preferences/me/`

### 4.11 Transport (Driver & Guardian)
- **Driver:**
  1. `POST /api/v1/transport/trips/start/`
  2. `POST /api/v1/transport/boarding-events/scan/` (with `idempotency_key` for offline queue safety)
  3. `POST /api/v1/transport/gps/ping/`
  4. `POST /api/v1/transport/trips/{id}/end/`
- **Guardian:**
  1. `GET /api/v1/transport/live-locations/latest/?route=<route_id>`
  2. `GET /api/v1/transport/boarding-events/?student=<student_id>`

### 4.12 Security / Gate Pickup Verification
1. `GET /api/v1/guardians/pickups/?student=<student_id>` — verify authorized pickup person
2. `POST /api/v1/guardians/pickups/{id}/send-otp/` → `POST /api/v1/guardians/pickups/{id}/verify-otp/`

### 4.13 Staff Self-Service & Payroll
- **Staff Payslips:**
  1. `GET /api/v1/payroll/payslips/?staff=<staff_id>` — list payslips for authenticated teacher or staff member (includes gross pay, deductions, net salary, payment status, and disbursement method)
  2. `GET /api/v1/payroll/payslips/{id}/download_pdf/` — download official PDF salary payslip
- **Staff Salary Structure & Profiles (Management / HR):**
  1. `GET /api/v1/payroll/structures/` — list configured institution salary allowance/deduction structures
  2. `GET /api/v1/payroll/profiles/` — list staff salary profiles
  3. `POST /api/v1/payroll/profiles/sync-roster/` — bulk initialize baseline salary profiles for newly appointed or unconfigured staff members without profiles

---

## 5. Error Codes & Client Handling

`apps/core/exceptions.py` (`custom_exception_handler`) wraps all DRF/application errors into a uniform envelope:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable summary",
  "details": {}
}
```

| HTTP Status | `code` | Meaning | Flutter Client Action |
|-------------|--------|---------|-----------------------|
| `400` | `VALIDATION_ERROR` | Field/business validation failure (`details` has field map or list). | Display field-level errors on form; show localized toast for non-field errors. |
| `400` | `APPLICATION_ERROR` (or custom `default_code.upper()`) | Domain rule error (`ApplicationError`). | Show `message` to user; do not retry automatically. |
| `401` | `AUTHENTICATION_REQUIRED` | Missing, malformed, or expired JWT access token. | Attempt single-flight `POST /api/v1/auth/refresh/`; if refresh fails (`401`), clear tokens and redirect to Login. |
| `403` | `PERMISSION_DENIED` | Authenticated user lacks role/object/tenant permission. | Show "Access Denied" state; do not retry. |
| `404` | `NOT_FOUND` | Resource does not exist or belongs to another tenant. | Show empty/not-found UI; remove stale item from local cache. |
| `429` | `ACCOUNT_LOCKED` / `THROTTLED` | 5 failed logins (15 min lock) or DRF rate limit. | Show lockout countdown / retry-after message; disable submit briefly. |
| `500` | `INTERNAL_SERVER_ERROR` | Unhandled server exception. | Show generic retryable error; log correlation info (never log tokens/PII). |
| `200` | `TOTP_REQUIRED` | Special login response when `is_totp_enabled=True`. | See **Section 11 (GAPS)** — no `/totp/verify/` endpoint exists yet. |

---

## 6. Pagination, Filtering, Date/Time/Timezone & Money

### Pagination (`apps/core/pagination.py`)
- Class: `StandardResultsSetPagination`
- Query params: `?page=1&page_size=20` (`max_page_size = 100`)
- Response envelope:
```json
{
  "count": 142,
  "next": "https://.../api/v1/.../?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Filtering, Search & Ordering
Configured globally in `REST_FRAMEWORK`:
- `DjangoFilterBackend`: exact query params per viewset (e.g., `?student=<uuid>&status=unpaid`)
- `SearchFilter`: `?search=<query>`
- `OrderingFilter`: `?ordering=-created_at` (prefix `-` for descending)

### Date, Time & Timezone Conventions
- Server `TIME_ZONE = "Asia/Dhaka"` (`UTC+6`), `USE_TZ = True`.
- Datetimes are serialized in ISO 8601 format (e.g., `2026-11-12T14:30:00+06:00` or `Z`).
- Dates use `YYYY-MM-DD`; times use `HH:MM:SS`.
- Flutter client should parse ISO 8601 strings to `DateTime` and display in `Asia/Dhaka` (`UTC+6`), formatting Bangla digits when `locale == 'bn'`.

### Money Format
- Currency: Bangladeshi Taka (`BDT`, symbol `৳`).
- Backend fields: `DecimalField(max_digits=12, decimal_places=2)` serialized by DRF as **decimal strings** (e.g., `"1500.00"`), never floats.
- Flutter client should parse amounts using `Decimal` or integer paisa (`* 100`) for calculations; never use binary `double` arithmetic for fee totals.

---

## 7. Push Notification Payload & `reference_id` Mapping

> **Field name note:** The prompt mentions `entity_id`; the backend actually sends **`reference_id`** in the FCM `data` map (`apps/communications/services/notification_service.py` line 158: `data={"event_type": event_type, "reference_id": str(reference_id or "")}`).

### FCM Payload Structure
```json
{
  "notification": {
    "title": "...",
    "body": "..."
  },
  "data": {
    "event_type": "<event_type>",
    "reference_id": "<uuid-string-or-empty>"
  }
}
```

### Implemented `event_type` Values & `reference_id` Targets

| `event_type` | `source_module` | `reference_id` points to | Suggested Deep Link |
|--------------|-----------------|--------------------------|---------------------|
| `homework_assigned` | `homework` | `Homework` UUID | `/homework/{reference_id}` |
| `homework_graded` | `homework` | `HomeworkSubmission` UUID | `/homework/submission/{reference_id}` |
| `homework_due_soon` | `homework` | `Homework` UUID | `/homework/{reference_id}` |
| `event_reminder` | `events` | `Event` UUID | `/events/{reference_id}` |
| `hostel_gatepass_otp` | `hostel` | `GatePass` UUID | `/hostel/gate-passes/{reference_id}` |
| `hostel_curfew_overdue` | `hostel` | `GatePass` UUID | `/hostel/gate-passes/{reference_id}` |
| `transport_boarded` / `transport_alighted` (`transport_<BoardingEventType>`) | `transport` | `BoardingEvent` UUID | `/transport/boarding/{reference_id}` |
| `library_overdue` | `library` | `BookIssue` UUID | `/library/issues` |
| `library_reservation_ready` | `library` | `BookReservation` UUID | `/library/reservations` |

*(See **Section 11 (GAPS)** for planned events like `attendance_absent`, `fee_invoice_issued`, `exam_result`, `notice_published`, and `chat_message` that are not yet wired to `dispatch_notification_event`.)*

---

## 8. Idempotency Keys & Offline-Queue-Safe Endpoints

Only two backend endpoints currently enforce database-level idempotency via `idempotency_key` (unique per `(institution, idempotency_key)`):

1. **`POST /api/v1/transport/boarding-events/scan/`**
   - Body includes `"idempotency_key": "<client-uuid>"`.
   - Replaying the same key returns `200 OK` with the existing `BoardingEvent` instead of creating a duplicate (`201 Created` on first insert). **Safe for offline queue replay.**
2. **`POST /api/v1/fees/payments/counter/`**
   - Body includes `"idempotency_key": "<client-uuid>"`.
   - Unique constraint `["institution", "idempotency_key"]` on `Payment` prevents duplicate counter collections on retry. **Safe for offline queue replay.**

### Other Safe / Partially Safe Endpoints
- `POST /api/v1/communications/device-tokens/` — idempotent upsert on `(institution, user, token)`.
- `POST /api/v1/events/notice-receipts/mark-read/` — safe to retry.
- `POST /api/v1/communications/chat/threads/{id}/mark-read/` — safe to retry.
- **Not idempotent (do NOT blindly replay without dedup):**
  - `POST /api/v1/communications/chat/threads/{id}/messages/` (creates duplicate messages if retried)
  - `POST /api/v1/attendance/mobile-checkin/checkin/` (no `idempotency_key` field)
  - `POST /api/v1/homework/assignments/{id}/submit/`

---

## 9. File Upload & Download Rules

### Homework & Learning Attachments (`config/settings/base.py` & `apps/homework/services/storage_service.py`)
- **Max file size:** `10 MB` (`HOMEWORK_MAX_FILE_SIZE_MB = 10`, configurable via env).
- **Allowed extensions:** `.pdf`, `.doc`, `.docx`, `.ppt`, `.pptx`, `.txt`, `.jpg`, `.jpeg`, `.png`, `.zip`.
- **Upload endpoints:**
  - `POST /api/v1/homework/assignments/{id}/upload_attachment/` (`multipart/form-data`, field `files` or `file`)
  - `POST /api/v1/homework/assignments/{id}/submit/` (`multipart/form-data`, field `files` or `file`, plus `text_response`)
- **Signed download URLs:**
  - Endpoint: `GET /api/v1/homework/download/?token=<hmac_token>`
  - TTL: `900 seconds` (`15 minutes`, `HOMEWORK_SIGNED_URL_TTL_SECONDS = 900`).
  - Requires `Authorization: Bearer <access_token>` AND tenant match (`token` is HMAC-signed and tenant-scoped; infected files with `av_scan_status == "infected"` return `403 PermissionDenied`).
  - **Flutter rule:** Never cache signed download URLs long-term; fetch fresh assignment/submission detail if a download returns `400`/`403` due to token expiry.

### PDF Downloads (Direct Binary Stream)
- `GET /api/v1/results/report-cards/{id}/download/` → `application/pdf`
- `GET /api/v1/exams/admit-cards/{id}/download_pdf/` → `application/pdf`
- `GET /api/v1/events/certificates/{id}/download-pdf/` → `application/pdf`

---

## 10. Seed / Demo Data & Command

### Available Command
```bash
python manage.py seed_demo_institution
```
- Defined in `apps/institutions/management/commands/seed_demo_institution.py`.
- **What it creates:**
  - `Institution`: `Dhaka Model High School & College` (`eiin = "134567"`, `code = "DMHSC"`, `timezone = "Asia/Dhaka"`)
  - `Branch`: `Main Campus` (`code = "MAIN"`)
  - `Shift`s: `Morning Shift`, `Day Shift`
  - `AcademicSession`: `2026` (`is_current = True`)
  - `Term`s: `First Term`, `Half Yearly`, `Annual Exam`
  - 2026 Bangladesh public holidays (`Holiday`)
- **What it does NOT create:** It does **not** create any demo `User` accounts (no guardian, student, teacher, admin, driver, or security test users). See **Section 11 (GAPS)**.

---

## 11. GAPS (Planned for Mobile vs. Current Backend)

1. **No `X-App-Version` Enforcement:** Backend does not inspect `X-App-Version` header or return `426 Upgrade Required` for force-update checks.
2. **2FA (`TOTP_REQUIRED`) Incomplete:** `POST /api/v1/auth/login/` returns `{"code": "TOTP_REQUIRED", "user_id": "..."}` when `is_totp_enabled=True`, but there is no `/api/v1/auth/totp/verify/` URL route in `apps/accounts/urls.py` to complete 2FA login.
3. **Password Reset Routes Missing:** `PasswordResetRequestSerializer` and `PasswordResetConfirmSerializer` exist in `apps/accounts/serializers.py`, but no `/password/reset/` URL routes are wired in `apps/accounts/urls.py`.
4. **Push Payload Uses `reference_id`, Not `entity_id`:** FCM `data` payload uses `"reference_id"` instead of `"entity_id"`.
5. **Missing Push Triggers for Core Mobile Events:** `NotificationEvent` docstring mentions `attendance_absent`, `fee_invoice_issued`, `exam_result`, and `chat_message`/`notice_published` are core mobile flows, but `dispatch_notification_event` is currently only wired in `homework`, `events`, `hostel`, `transport`, and `library`—not in `attendance`, `fees`, `results`, or `communications` (`NoticeViewSet` / `chat_service`).
6. **No Seeded Demo Users:** `seed_demo_institution` only seeds institution/academic/holiday records. Mobile QA requires creating test users manually (via Django admin, `createsuperuser`, or `/api/v1/auth/users/`) or adding a `seed_demo_users` management command.
7. **Driver User Linkage & Security Gate Endpoints:** `Driver` and `security` `user_type`s exist, and `BoardingEventViewSet.scan` resolves `driver` via `resolve_driver_for_user(user)`, but there is no dedicated `/api/v1/driver/me/` or dedicated `/api/v1/security/gate-logs/` endpoint—security uses `guardians/pickups/` and `hostel/gate-passes/`.
8. **Offline Check-in Idempotency:** `POST /api/v1/attendance/mobile-checkin/checkin/` does not accept an `idempotency_key`, making offline-queued staff check-ins unsafe to replay without server-side deduplication.

---

## 12. Flutter Client Synchronization & Contract Guidelines

### 12.1 Schema as Single Source of Truth
The canonical OpenAPI 3.0 specification file is located at:
```
schema/schema.yml
```
Whenever backend models, serializers, or query parameters change, the backend team regenerates and validates this file with:
```bash
venv/bin/python manage.py spectacular --file schema/schema.yml --validate
```

### 12.2 Syncing the Flutter Codebase
In the separate Flutter repository:
1. Pull or copy the updated `schema/schema.yml` into your mobile project's schema directory (or reference the backend repository submodule/path).
2. Run Flutter build runner to update freezed DTOs and API clients:
   ```bash
   dart run build_runner build --delete-conflicting-outputs
   ```
3. Verify that all network request bodies, query filters, and response models conform strictly to the generated types without manual overrides.
4. Run Flutter test suite:
   ```bash
   flutter test
   ```

### 12.3 Cross-Repository Parity Checklist
- [ ] No hardcoded endpoints or request/response structures in mobile code.
- [ ] Dates parsed using standard ISO 8601 parsers and formatted for `Asia/Dhaka` (`UTC+6`).
- [ ] All money fields handled via `Decimal` (or integer paisa) to maintain financial integrity.
- [ ] All API error responses mapped to strongly typed `Failure` classes using the `{ code, message, details }` envelope.
- [ ] Offline actions check for `idempotency_key` support before enqueueing retries.
