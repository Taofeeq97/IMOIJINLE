from django.contrib import admin

from apps.orgsettings.models import (
    ApplicationFeeSettings,
    BrandSettings,
    FeatureFlag,
    PaymentGatewaySettings,
    SiteSettings,
)

admin.site.register(BrandSettings)
admin.site.register(SiteSettings)
admin.site.register(FeatureFlag)
admin.site.register(PaymentGatewaySettings)
admin.site.register(ApplicationFeeSettings)
