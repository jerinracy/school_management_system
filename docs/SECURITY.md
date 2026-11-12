# Security Architecture & OWASP ASVS-Lite Review

## 1. Security Controls Implemented
- **Authentication & Passwords**:
  - Argon2 (`Argon2PasswordHasher`) primary password hashing with PBKDF2 fallback.
  - Short-lived JWT access tokens with refresh token rotation & blacklisting (`rest_framework_simplejwt.token_blacklist`).
  - Brute-force lockout & OTP attempt limits (`apps/accounts/services/auth.py`).
- **Admin 2FA & IP Restrictions (`apps/core/middleware.py`)**:
  - `ENFORCE_ADMIN_2FA=True` (enabled by default in `config/settings/prod.py`) blocks `SUPERADMIN` and `ADMIN` accounts on non-auth API endpoints until `is_totp_enabled=True`.
  - `ADMIN_ALLOWED_IPS` (env) and `institution.settings["admin_allowed_ips"]` allow restricting admin access to trusted IP addresses or CIDR ranges.
- **HTTP Security Headers & TLS (`config/settings/prod.py`, `apps/core/middleware.py`)**:
  - `SECURE_SSL_REDIRECT=True`, `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https")`, `SECURE_HSTS_SECONDS=31536000` (with `includeSubDomains` and `preload`).
  - `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `CSRF_COOKIE_SECURE=True`, `CSRF_COOKIE_HTTPONLY=True`, `X_FRAME_OPTIONS="DENY"`.
  - `SecurityHeadersMiddleware` sets `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, and optional `Content-Security-Policy`.
- **Field-Level Encryption & Key Rotation (`apps/core/utils/encryption.py`)**:
  - Uses `cryptography.fernet.MultiFernet` (AES-128-CBC + HMAC-SHA256) with `FIELD_ENCRYPTION_KEYS` (comma-separated Fernet keys, newest first).
  - **Key Rotation Procedure**:
    1. Generate a new key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
    2. Prepend the new key to `FIELD_ENCRYPTION_KEYS` (`NEW_KEY,OLD_KEY`) and deploy.
    3. Run `rotate_ciphertext()` over stored encrypted fields to re-encrypt under `NEW_KEY`.
    4. Remove `OLD_KEY` from `FIELD_ENCRYPTION_KEYS` after all rows are rotated.
- **PII & Biometric Protection**:
  - Raw biometric images are never stored (`apps/devices`); only templates/device IDs with `BiometricConsent`.
  - `apps/audit` redacts secrets (`password`, `token`, `secret`, `otp`, `nid`, `biometric`) and masks BD phone numbers (`+88017****5678`).
  - `apps/events` gates student photos/videos behind `guardian_consent_verified=True` and `is_approved=True`.

## 2. OWASP ASVS-Lite Review Checklist
| Area | Requirement | Status | Notes |
|------|-------------|--------|-------|
| V2 Auth | Argon2 hashing, lockout, TOTP 2FA for admins | PASS | Enforced via `AdminSecurityMiddleware` in prod |
| V3 Session | HttpOnly/Secure cookies, JWT refresh blacklist | PASS | Configured in `config/settings/prod.py` |
| V4 Access Control | Deny-by-default RBAC + `TenantScopedMixin` | PASS | Tested across all 26 tasks |
| V5 Input Validation | DRF serializers + whitelisted report builder | PASS | Zero raw SQL in `apps/reports` |
| V6 Cryptography | `MultiFernet` field encryption + TLS/HSTS | PASS | Key rotation via `rotate_ciphertext` |
| V7 Logging | Immutable `AuditLog` + PII redaction filter | PASS | `apps/audit` append-only |
| V12 Files | Extension & size validation on uploads | PASS | Enforced in `homework`, `events`, `reports` |
