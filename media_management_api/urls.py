from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("media_management_api.media_auth.urls")),
    path("api/", include("media_management_api.media_service.urls")),
    path("", RedirectView.as_view(url="/api/", permanent=False), name="index"),
]
