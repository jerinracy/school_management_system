"""Production settings."""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# Production Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
ENFORCE_ADMIN_2FA = env.bool("ENFORCE_ADMIN_2FA", default=True)
REQUIRE_EXPLICIT_ENCRYPTION_KEYS = env.bool("REQUIRE_EXPLICIT_ENCRYPTION_KEYS", default=True)

# Optional SQL / Slow-Query Logging
if env.bool("LOG_SQL_QUERIES", default=False):
    LOGGING["loggers"]["django.db.backends"] = {  # type: ignore[index]  # noqa: F405
        "handlers": ["console"],
        "level": "DEBUG",
        "propagate": False,
    }

# Sentry error tracking
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,
    )

# Vite production settings
DJANGO_VITE["default"]["dev_mode"] = False  # noqa: F405
