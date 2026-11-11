---
name: flutter-offline-and-notifications
description: Use for caching/offline behavior, background sync, FCM push notifications, deep links, geofenced check-in, camera/location permissions, and app-lock biometrics in the Flutter app.
---

# flutter-offline-and-notifications

### Offline
- Drift tables per cached resource with `fetched_at`; **stale-while-revalidate**: render cache → refresh → update.
- Write queue for offline actions (teacher attendance, leave request) with idempotency keys, retry, and conflict handling; show "pending sync" badges.
- Use `connectivity_plus` as a hint only; real failures come from requests.

### Push (FCM)
- Register token after login, send to backend with device info; unregister on logout; refresh on token change.
- Channels (Android): attendance, fees, results, notices, emergency (high importance).
- Notification payload carries `type` + `entity_id` → deep link via go_router; handle foreground/background/terminated.
- Respect user notification preferences from backend.

### Staff check-in
- Permission rationale screens; geofence check (radius from institution config) + selfie; send device time + GPS accuracy; handle mock-location detection flag; offline queue allowed only if policy permits.

### App lock
- `local_auth` for biometric/PIN lock on resume after N minutes; tokens remain in secure storage; fallback to password/OTP.
