from django.conf.urls import url, include
from django.contrib import admin
from rest_framework.urlpatterns import format_suffix_patterns
from media_service import views

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

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^$', views.APIRoot.as_view(), name="api-root"),
    url(r'^courses/$', course_list, name='course-list'),
    url(r'^courses/(?P<lti_context>lti/)?(?P<pk>[^/.]+)/$', course_detail, name='course-detail'),
    url(r'^courses/(?P<lti_context>lti/)?(?P<pk>[^/.]+)/collections/$', views.CourseCollectionsView.as_view(), name='course-collections'),
    url(r'^courses/(?P<lti_context>lti/)?(?P<pk>[^/.]+)/images/$', views.CourseImagesListView.as_view(), name='courseimages-list'),
    url(r'^collections/$', collection_list, name='collection-list'),
    url(r'^collections/(?P<pk>[^/.]+)/$', collection_detail, name='collection-detail'),
    url(r'^collections/(?P<pk>[^/.]+)/images/$', views.CollectionImagesListView.as_view(), name='collectionimages-list'),
    url(r'^collection-images/(?P<pk>[^/.]+)/$', views.CollectionImagesDetailView.as_view(), name='collectionimages-detail'),
    url(r'^course-images/$', image_list, name='courseimage-list'),
    url(r'^course-images/(?P<pk>[^/.]+)/$', image_detail, name='courseimage-detail'),
    url(r'^course-images/(?P<pk>[^/.]+)/upload$', views.ImageUploadView.as_view(), name='courseimage-upload'),
]

urlpatterns = format_suffix_patterns(urlpatterns)