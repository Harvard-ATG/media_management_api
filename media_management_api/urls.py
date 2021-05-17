from django.urls import include, path
from django.contrib import admin
from django.views.generic.base import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('media_management_api.media_auth.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtian_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('media_management_api.media_service.urls')),
    path('', RedirectView.as_view(url='/api/', permanent=False), name='index'),
]
