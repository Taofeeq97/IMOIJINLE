from apps.accounts.models import Profile


def ensure_profile(sender, instance, created, **kwargs):  # type: ignore[no-untyped-def]
    if created:
        Profile.objects.get_or_create(user=instance)
