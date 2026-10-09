from django.contrib import admin

from apps.certificates import models

admin.site.register(models.CertificateTemplate)
admin.site.register(models.CertificateTemplateVersion)
admin.site.register(models.CertificateIssueRule)
admin.site.register(models.Certificate)
admin.site.register(models.CertificateVerificationLog)
