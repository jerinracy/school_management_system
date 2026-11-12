"""Base Django settings for School Management System."""

import re
from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Read .env if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# Core Security & Debug
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-in-production-1234567890")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "django_vite",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.institutions.apps.InstitutionsConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.academics.apps.AcademicsConfig",
    "apps.admissions.apps.AdmissionsConfig",
    "apps.students.apps.StudentsConfig",
    "apps.guardians.apps.GuardiansConfig",
    "apps.staff.apps.StaffConfig",
    "apps.devices.apps.DevicesConfig",
    "apps.attendance.apps.AttendanceConfig",
    "apps.exams.apps.ExamsConfig",
    "apps.results.apps.ResultsConfig",
    "apps.fees.apps.FeesConfig",
    "apps.communications.apps.CommunicationsConfig",
    "apps.accounting.apps.AccountingConfig",
    "apps.payroll.apps.PayrollConfig",
    "apps.homework.apps.HomeworkConfig",
    "apps.library.apps.LibraryConfig",
    "apps.transport.apps.TransportConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
# Connect to PostgreSQL by default; fallback to SQLite if postgres not running locally
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Password Hashers (Argon2 by default)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization & Localization
# Default to Asia/Dhaka and English with Bangla enabled
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("bn", "Bangla"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = (
    [
        BASE_DIR / "frontend" / "dist",
    ]
    if (BASE_DIR / "frontend" / "dist").exists()
    else []
)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Homework & Learning File Upload / Signed URL Configuration
HOMEWORK_MAX_FILE_SIZE_MB = env.int("HOMEWORK_MAX_FILE_SIZE_MB", default=10)
HOMEWORK_SIGNED_URL_TTL_SECONDS = env.int("HOMEWORK_SIGNED_URL_TTL_SECONDS", default=900)
HOMEWORK_ALLOWED_EXTENSIONS = [
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
    ".zip",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS & CSRF
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
)

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
}

# SimpleJWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# drf-spectacular Settings
SPECTACULAR_SETTINGS = {
    "TITLE": "School Management System API (Bangladesh)",
    "DESCRIPTION": (
        "Production-grade Multi-Tenant School Management API for Bangladeshi Institutions. "
        "Supports Biometric Attendance, Admission, GPA 5.0 Examination, and Multi-Gateway Fees."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
}

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Redis Cache
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# django-vite Settings
DJANGO_VITE = {
    "default": {
        "dev_mode": env.bool("VITE_DEV_MODE", default=DEBUG),
        "dev_server_host": env("VITE_DEV_SERVER_HOST", default="localhost"),
        "dev_server_port": env.int("VITE_DEV_SERVER_PORT", default=5173),
        "manifest_path": BASE_DIR / "frontend" / "dist" / "manifest.json",
    }
}


# Custom Logging with PII Redaction Filter
class PIIRedactionFilter:
    """Filter to redact sensitive data (BD phones, NID, biometric tokens) from logs."""

    # Redact BD phones (+8801XXXXXXXXX or 01XXXXXXXXX)
    PHONE_REGEX = re.compile(r"(\+?8801|01)[3-9]\d{8}")
    # Redact NID numbers (10, 13, or 17 digits)
    NID_REGEX = re.compile(r"\b\d{10}\b|\b\d{13}\b|\b\d{17}\b")

    def filter(self, record: object) -> bool:
        if isinstance(record.msg, str):  # type: ignore[attr-defined]
            msg = record.msg  # type: ignore[attr-defined]
            msg = self.PHONE_REGEX.sub("[PHONE_REDACTED]", msg)
            msg = self.NID_REGEX.sub("[NID_REDACTED]", msg)
            record.msg = msg  # type: ignore[attr-defined]
        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "pii_redaction": {
            "()": PIIRedactionFilter,
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["pii_redaction"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# Transport GPS live location retention policy (days)
TRANSPORT_LOCATION_RETENTION_DAYS = env.int("TRANSPORT_LOCATION_RETENTION_DAYS", default=30)
