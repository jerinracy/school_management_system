"""Development settings."""

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

# Vite dev mode
DJANGO_VITE["default"]["dev_mode"] = True  # noqa: F405
