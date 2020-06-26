from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

app_name = 'iiif'

urlpatterns = [
    path('', views.IiifView.as_view(), name="root"),
    path('collections/', views.IiifCollectionsView.as_view(), name='collections'),
    path('collection/<int:pk>/', views.IiifCollectionView.as_view(), name='collection'),
    path('manifest/<int:manifest_id>/', views.IiifManifestView.as_view(), name='manifest'),
    path('manifest/<int:manifest_id>/<str:object_type>/<int:object_id>/', views.IiifManifestView.as_view(), name='manifest-object'),
]
