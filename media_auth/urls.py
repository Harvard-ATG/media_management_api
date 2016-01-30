from django.conf.urls import url, include
from django.views.generic.base import RedirectView
from . import views 

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^create-token$', views.create_token, name='create-token'),
    url(r'^check-token/(?P<token_key>.+)$', views.check_token, name='check-token'),
    url(r'^destroy-token/(?P<token_key>.+)$', views.destroy_token, name='destroy-token'),
]