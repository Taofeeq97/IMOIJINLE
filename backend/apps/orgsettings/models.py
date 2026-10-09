from django.db import models

from apps.common.models import BaseModel


class BrandSettings(BaseModel):
    """Singleton-ish branding configuration (latest row wins)."""

    org_name = models.CharField(max_length=128, default="Imo Ijinle Academy")
    logo_url = models.URLField(blank=True)
    favicon_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=16, default="#1F5C4D")
    accent_color = models.CharField(max_length=16, default="#C8943A")
    background_color = models.CharField(max_length=16, default="#FBFAF7")
    foreground_color = models.CharField(max_length=16, default="#16201C")
    ink_color = models.CharField(max_length=16, default="#14201C")
    ink2_color = models.CharField(max_length=16, default="#1E2C27")
    ink_foreground = models.CharField(max_length=16, default="#F4F2EC")
    font_display = models.CharField(max_length=64, default="Fraunces")
    font_ui = models.CharField(max_length=64, default="Inter")
    extra_css_vars = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Brand settings"

    def __str__(self) -> str:
        return self.org_name

    @classmethod
    def get_solo(cls) -> "BrandSettings":
        obj = cls.objects.order_by("-updated_at").first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class SiteSettings(BaseModel):
    base_url = models.URLField(default="http://localhost:3000")
    support_email = models.EmailField(default="support@imoijinle.local")
    default_timezone = models.CharField(max_length=64, default="Africa/Lagos")
    default_locale = models.CharField(max_length=16, default="en")
    application_grace_for_closed_cohorts = models.BooleanField(default=True)
    require_fee_before_admit = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Site settings"

    @classmethod
    def get_solo(cls) -> "SiteSettings":
        obj = cls.objects.order_by("-updated_at").first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class FeatureFlag(BaseModel):
    key = models.SlugField(unique=True)
    enabled = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.key


class PaymentMode(models.TextChoices):
    TEST = "test", "Test"
    LIVE = "live", "Live"


class PaymentGatewaySettings(BaseModel):
    mode = models.CharField(max_length=8, choices=PaymentMode.choices, default=PaymentMode.TEST)
    public_key = models.CharField(max_length=255, blank=True)
    secret_key_encrypted = models.TextField(blank=True)
    default_currency = models.CharField(max_length=3, default="NGN")
    channel_card = models.BooleanField(default=True)
    channel_bank = models.BooleanField(default=True)
    channel_ussd = models.BooleanField(default=True)
    channel_transfer = models.BooleanField(default=True)
    channel_mobile_money = models.BooleanField(default=False)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_ok = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Payment gateway settings"

    @classmethod
    def get_solo(cls) -> "PaymentGatewaySettings":
        obj = cls.objects.order_by("-updated_at").first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class ApplicationFeeSettings(BaseModel):
    default_amount_kobo = models.BigIntegerField(default=500000)
    is_free = models.BooleanField(default=False)
    refundable_policy = models.JSONField(default=dict, blank=True)
    fee_required_before_admit = models.BooleanField(default=True)
    waiver_codes = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name_plural = "Application fee settings"

    @classmethod
    def get_solo(cls) -> "ApplicationFeeSettings":
        obj = cls.objects.order_by("-updated_at").first()
        if obj is None:
            obj = cls.objects.create()
        return obj
