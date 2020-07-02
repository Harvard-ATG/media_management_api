from django.urls import path, re_path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

app_name = 'iiif'

urlpatterns = [
    path('', views.IiifView.as_view(), name="root"),
    path('collections', views.IiifCollectionsView.as_view(), name='collections'),
    path('collection/<int:pk>', views.IiifCollectionView.as_view(), name='collection'),
    path('manifest/<int:manifest_id>', views.IiifManifestView.as_view(), name='manifest'),
    re_path(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>sequence)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='sequence'),
    re_path(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>canvas)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='canvas'),
    re_path(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>annotation)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='annotation'),
    re_path(r'^manifest/(?P<manifest_id>\d+)/(?P<object_type>resource)/(?P<object_id>[0-9.-]+)$', views.IiifManifestView.as_view(), name='resource'),
]
