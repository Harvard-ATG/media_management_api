from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic.base import RedirectView

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/auth/', include('media_auth.urls', namespace='api-auth')),
    url(r'^api/', include('media_service.urls')),
    url(r'^iiif/', include('iiif_service.urls', namespace='iiif')),
    url(r'^$', RedirectView.as_view(url='/api/', permanent=False), name='index'),
]