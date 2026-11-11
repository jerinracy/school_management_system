---
name: biometric-device-integration
description: Use for any task touching biometric/RFID/QR/face devices, punch ingestion, device enrollment, or attendance-rule processing. Defines the vendor-agnostic adapter architecture and safe handling of biometric data.
---

# biometric-device-integration

### Architecture
```
Device (ZKTeco / Hikvision / Suprema / eSSL / generic HTTP / mobile app)
   │  (push: ADMS/HTTP webhook | pull: SDK/poll via connector)
   ▼
DeviceAdapter (per vendor)  →  normalise  →  RawPunch (immutable, stored as-received)
   ▼
PunchProcessor (Celery)  →  dedupe  →  identity resolve  →  AttendanceEvent
   ▼
AttendanceRuleEngine (per user-type policy)  →  DailyAttendance  →  notifications
```
### Rules
- **Adapter interface:** `authenticate()`, `fetch_logs(since)`, `parse_push(payload)`, `enroll_user(user, template|card|pin)`, `remove_user()`, `get_health()`; register adapters in a registry keyed by `device.vendor` + `device.protocol`.
- **Never store raw fingerprint/face images.** Store vendor template reference or device-side user ID; track **consent** (who, when, version).
- Immutable `RawPunch` log (payload hash, device SN, received_at, device_time); processing is replayable and idempotent (unique `(device, user_ref, punch_time)`).
- **Clock drift:** record device time and server time; flag drift > threshold; allow per-device timezone/offset.
- Duplicate-punch window configurable (e.g. 60s).
- **Offline devices:** buffer & backfill; late-arriving punches recompute the affected day only.
- **Identity mapping:** `DeviceUserMap(device, device_user_id → student/staff)`; unmapped punches go to a review queue.
- **Policies per user type & device group:** methods allowed/required, shifts, grace, late/half-day/early-leave, multi-punch/period-wise, holiday/leave/exam overrides.
- **Manual correction:** requires reason + approver, writes audit log, never mutates RawPunch.
- **Security:** device auth by shared secret/token + IP allow-list option; verify signatures; rate-limit device endpoints.
- **Simulators:** provide a `FakeDevice` adapter + management command to generate punches for tests/demo.
- Notifications on arrival/exit/absence are async, deduplicated, and respect quiet hours.

---
