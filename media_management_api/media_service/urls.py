from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns
import views
import iiif.urls

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
    url(r'^$', views.APIRoot.as_view(), name="root"),
    url(r'^courses$', course_list, name='course-list'),
    url(r'^courses/(?P<pk>\d+)$', course_detail, name='course-detail'),
    url(r'^courses/(?P<pk>\d+)/course_copy', views.CourseCopyView.as_view(), name='course-clones'),
    url(r'^courses/(?P<pk>\d+)/collections$', views.CourseCollectionsView.as_view(), name='course-collections'),
    url(r'^courses/(?P<pk>\d+)/images$', views.CourseImagesListView.as_view(), name='course-images'),
    url(r'^collections$', collection_list, name='collection-list'),
    url(r'^collections/(?P<pk>\d+)$', collection_detail, name='collection-detail'),
    url(r'^collections/(?P<pk>\d+)/images$', views.CollectionImagesListView.as_view(), name='collectionimages-list'),
    url(r'^collection-images/(?P<pk>\d+)$', views.CollectionImagesDetailView.as_view(), name='collectionimages-detail'),
    url(r'^images$', image_list, name='image-list'),
    url(r'^images/(?P<pk>\d+)$', image_detail, name='image-detail'),
    url(r'^iiif/', include(iiif.urls, namespace='iiif')),

]

urlpatterns = format_suffix_patterns(urlpatterns)
