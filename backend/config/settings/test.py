"""Django settings for pytest / CI."""

import os

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# CI provides Postgres via DATABASE_URL; local unit tests use in-memory SQLite.
_use_postgres = os.environ.get("GITHUB_ACTIONS", "").lower() in {"1", "true"} or os.environ.get(
    "USE_POSTGRES_TESTS", ""
).lower() in {"1", "true", "yes"}
_database_url = os.environ.get("DATABASE_URL", "")
if not (_use_postgres and _database_url.startswith("postgres")):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}
