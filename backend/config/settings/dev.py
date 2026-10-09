import sys

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")  # noqa: F405
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))  # noqa: F405

# Prefer SQLite for unit tests / local without Docker
if "pytest" in sys.modules or os.environ.get("USE_SQLITE", "").lower() in {"1", "true"}:  # noqa: F405
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:" if "pytest" in sys.modules else str(BASE_DIR / "dev.sqlite3"),  # noqa: F405
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True  # noqa: F405
