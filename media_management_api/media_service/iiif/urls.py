from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    url(r'^$', views.IiifView.as_view(), name="root"),
    url(r'^collections$', views.IiifCollectionsView.as_view(), name='collections'),
    url(r'^collection/(?P<pk>\d+)$', views.IiifCollectionView.as_view(), name='collection'),
    url(r'^manifest/(?P<manifest_id>\d+)$', views.IiifManifestView.as_view(), name='manifest'),
    url(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>sequence)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='sequence'),
    url(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>canvas)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='canvas'),
    url(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>annotation)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='annotation'),
    url(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>resource)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='resource'),
]
