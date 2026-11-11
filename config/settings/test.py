"""Testing settings for fast test execution."""

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret-key-fast-testing-hashers-only"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# In-memory cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Celery tasks run synchronously during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable Vite in tests
DJANGO_VITE["default"]["dev_mode"] = False  # noqa: F405
