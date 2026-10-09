from django.urls import path

from apps.certificates import views

urlpatterns = [
    path(
        "certificate-templates",
        views.CertificateTemplateListCreateView.as_view(),
        name="certificate-templates",
    ),
    path(
        "certificate-templates/<uuid:template_id>",
        views.CertificateTemplateDetailView.as_view(),
        name="certificate-template-detail",
    ),
    path(
        "certificate-templates/<uuid:template_id>/preview",
        views.CertificateTemplatePreviewView.as_view(),
        name="certificate-template-preview",
    ),
    path(
        "certificate-templates/<uuid:template_id>/publish",
        views.CertificateTemplatePublishView.as_view(),
        name="certificate-template-publish",
    ),
    path(
        "certificate-issue-rules",
        views.CertificateIssueRuleListCreateView.as_view(),
        name="certificate-issue-rules",
    ),
    path(
        "certificate-issue-rules/<uuid:rule_id>",
        views.CertificateIssueRuleDetailView.as_view(),
        name="certificate-issue-rule-detail",
    ),
    path("certificates", views.CertificateListView.as_view(), name="certificates-list"),
    path("certificates/issue", views.CertificateIssueView.as_view(), name="certificates-issue"),
    path(
        "certificates/<uuid:certificate_id>/revoke",
        views.CertificateRevokeView.as_view(),
        name="certificates-revoke",
    ),
    path("me/certificates", views.MeCertificatesView.as_view(), name="me-certificates"),
    path(
        "public/certificates/verify/<str:code>",
        views.PublicCertificateVerifyView.as_view(),
        name="public-certificate-verify",
    ),
]
