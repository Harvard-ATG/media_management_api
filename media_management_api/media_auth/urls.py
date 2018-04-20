from django.conf.urls import url, include
from . import views 

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^obtain-token$', views.obtain_token, name='obtain-token'),
    url(r'^check-token/(?P<access_token>.+)$', views.check_token, name='check-token'),
    url(r'^destroy-token/(?P<access_token>.+)$', views.destroy_token, name='destroy-token'),
]
