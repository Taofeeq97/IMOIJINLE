from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self) -> None:
        from django.db.models.signals import post_save

        from apps.accounts.models import User
        from apps.accounts.signals import ensure_profile

        post_save.connect(ensure_profile, sender=User)
