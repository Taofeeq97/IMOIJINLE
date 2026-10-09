"""Shared Django settings for Imo Ijinle Academy LMS."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me-imo-ijinle-lms")
DEBUG = False
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third party
    "corsheaders",
    "django_filters",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "storages",
    # Local
    "apps.common",
    "apps.accounts",
    "apps.audit",
    "apps.orgsettings",
    "apps.programs",
    "apps.courses",
    "apps.payments",
    "apps.admissions",
    "apps.integrations",
    "apps.learning",
    "apps.assessments",
    "apps.certificates",
    "apps.comms",
    "apps.search",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "imo_lms"),
        "USER": os.environ.get("POSTGRES_USER", "imo"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "imo"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Allow DATABASE_URL override
_database_url = os.environ.get("DATABASE_URL")
if _database_url and _database_url.startswith("postgres"):
    # simple parse: postgres://user:pass@host:port/db
    import re

    m = re.match(
        r"postgres(?:ql)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)",
        _database_url,
    )
    if m:
        DATABASES["default"] = {
            "ENGINE": "django.db.backends.postgresql",
            "USER": m.group(1),
            "PASSWORD": m.group(2),
            "HOST": m.group(3),
            "PORT": m.group(4),
            "NAME": m.group(5),
        }

AUTH_USER_MODEL = "accounts.User"
SITE_ID = 1

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_DISPLAY_TIMEZONE = os.environ.get("DEFAULT_DISPLAY_TIMEZONE", "Africa/Lagos")

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# MinIO / S3 when configured
AWS_ACCESS_KEY_ID = os.environ.get("MINIO_ACCESS_KEY", os.environ.get("AWS_ACCESS_KEY_ID", "minio"))
AWS_SECRET_ACCESS_KEY = os.environ.get(
    "MINIO_SECRET_KEY", os.environ.get("AWS_SECRET_ACCESS_KEY", "minio_secret_change_me")
)
AWS_STORAGE_BUCKET_NAME = os.environ.get("MINIO_BUCKET", "imo-lms")
AWS_S3_ENDPOINT_URL = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True

if os.environ.get("USE_S3", "").lower() in {"1", "true", "yes"}:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in {"1", "true"}
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "120/min",
        "auth": "10/min",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REFRESH_COOKIE_NAME = os.environ.get("REFRESH_COOKIE_NAME", "refresh_token")
REFRESH_COOKIE_PATH = "/api/v1/auth"
REFRESH_COOKIE_SAMESITE = os.environ.get("REFRESH_COOKIE_SAMESITE", "Lax")
REFRESH_COOKIE_SECURE = os.environ.get("REFRESH_COOKIE_SECURE", "false").lower() in {"1", "true"}
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN") or None

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()

SPECTACULAR_SETTINGS = {
    "TITLE": "Imo Ijinle Academy LMS API",
    "DESCRIPTION": "Spirit Science / Educational Portal API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "false").lower() in {"1", "true"}
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Academy <noreply@imoijinle.local>")

BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", BASE_URL)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Object storage (MinIO / S3) — required for content uploads
AWS_S3_PUBLIC_ENDPOINT_URL = os.environ.get(
    "AWS_S3_PUBLIC_ENDPOINT_URL", os.environ.get("MINIO_PUBLIC_ENDPOINT", AWS_S3_ENDPOINT_URL)
)

# Paystack
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_BASE_URL = os.environ.get("PAYSTACK_BASE_URL", "https://api.paystack.co")

# Mux video
MUX_TOKEN_ID = os.environ.get("MUX_TOKEN_ID", "")
MUX_TOKEN_SECRET = os.environ.get("MUX_TOKEN_SECRET", "")
MUX_WEBHOOK_SECRET = os.environ.get("MUX_WEBHOOK_SECRET", "")
MUX_SIGNING_KEY_ID = os.environ.get("MUX_SIGNING_KEY_ID", "")
MUX_SIGNING_PRIVATE_KEY = os.environ.get("MUX_SIGNING_PRIVATE_KEY", "")
MUX_PLAYBACK_POLICY = os.environ.get("MUX_PLAYBACK_POLICY", "signed")  # signed|public

# Document conversion (Gotenberg + LibreOffice)
DOCUMENT_CONVERTER_URL = os.environ.get("DOCUMENT_CONVERTER_URL", "http://localhost:3001")

CELERY_TASK_ROUTES = {
    "apps.integrations.tasks.convert_subtopic_content_task": {"queue": "media"},
    "apps.integrations.tasks.sync_mux_asset_task": {"queue": "media"},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
    )
