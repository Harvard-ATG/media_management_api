from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

app_name = 'api'

course_list = views.CourseViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
course_detail = views.CourseViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

collection_list = views.CollectionViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
collection_detail = views.CollectionViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

image_list = views.CourseImageViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
image_detail = views.CourseImageViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns = [
    path('', views.APIRoot.as_view(), name="root"),
    path('courses', course_list, name='course-list'),
    path('courses/search', views.CourseSearchView.as_view(), name='course-search'),
    path('courses/<int:pk>', course_detail, name='course-detail'),
    path('courses/<int:pk>/course_copy', views.CourseCopyView.as_view(), name='course-clones'),
    path('courses/<int:pk>/collections', views.CourseCollectionsView.as_view(), name='course-collections'),
    path('courses/<int:pk>/images', views.CourseImagesListView.as_view(), name='course-images'),
    path('courses/<int:pk>/library_export', views.CourseImagesListCsvExportView.as_view(), name='course-images-csv'),
    path('collections', collection_list, name='collection-list'),
    path('collections/<int:pk>', collection_detail, name='collection-detail'),
    path('collections/<int:pk>/images', views.CollectionImagesListView.as_view(), name='collectionimages-list'),
    path('collection-images/<int:pk>', views.CollectionImagesDetailView.as_view(), name='collectionimages-detail'),
    path('images', image_list, name='image-list'),
    path('images/<int:pk>', image_detail, name='image-detail'),
    path('iiif/', include('media_management_api.media_service.iiif.urls')),

]

urlpatterns = format_suffix_patterns(urlpatterns)
