from rest_framework import serializers

from apps.orgsettings.models import BrandSettings


class BrandSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandSettings
        fields = [
            "org_name",
            "logo_url",
            "favicon_url",
            "primary_color",
            "accent_color",
            "background_color",
            "foreground_color",
            "ink_color",
            "ink2_color",
            "ink_foreground",
            "font_display",
            "font_ui",
            "extra_css_vars",
        ]
