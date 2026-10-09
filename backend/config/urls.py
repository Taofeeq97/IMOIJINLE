from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/", include("apps.common.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/settings/", include("apps.orgsettings.urls")),
    path("api/v1/", include("apps.programs.urls")),
    path("api/v1/", include("apps.courses.urls")),
    path("api/v1/", include("apps.admissions.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/v1/", include("apps.learning.urls")),
    path("api/v1/", include("apps.assessments.urls")),
    path("api/v1/", include("apps.certificates.urls")),
    path("api/v1/", include("apps.comms.urls")),
    path("api/v1/", include("apps.search.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
