"""Development settings."""

import socket

from .base import *  # noqa: F403

DEBUG = True

# Add debug toolbar in development
INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
]

MIDDLEWARE = [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Vite dev mode: auto-detect if Vite dev server is running on localhost:5173;
# fallback to serving built assets from manifest.json so the dashboard loads cleanly
# even when `npm run dev` is not running.
_vite_dev_env = env.bool("VITE_DEV_MODE", default=None)  # noqa: F405
if _vite_dev_env is not None:
    DJANGO_VITE["default"]["dev_mode"] = _vite_dev_env  # noqa: F405
else:
    try:
        with socket.create_connection(("localhost", 5173), timeout=0.1):
            DJANGO_VITE["default"]["dev_mode"] = True  # noqa: F405
    except OSError:
        DJANGO_VITE["default"]["dev_mode"] = False  # noqa: F405
