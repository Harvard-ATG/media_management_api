from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, exceptions
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route, api_view
from rest_framework.reverse import reverse
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser, FileUploadParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied

import zipfile
from django.core.files.base import File
from django.core.files.uploadedfile import UploadedFile

import io
import os

from media_service.models import Course, Collection, Resource, MediaStore, CollectionResource
from media_service.mediastore import MediaStoreUpload
from media_service.iiif import CollectionManifestController
from media_service.serializers import UserSerializer, CourseSerializer, ResourceSerializer, CollectionSerializer, CollectionResourceSerializer

from media_auth.filters import CourseEndpointFilter, CollectionEndpointFilter, ResourceEndpointFilter
from media_auth.permissions import CourseEndpointPermission, CollectionEndpointPermission, ResourceEndpointPermission, CollectionResourceEndpointPermission

import logging

logger = logging.getLogger(__name__)

class APIRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'courses': reverse('course-list', request=request, format=format),
            'collections': reverse('collection-list', request=request, format=format),
            'images': reverse('image-list', request=request, format=format),
        })

class CourseViewSet(viewsets.ModelViewSet):
    '''
A **course** resource contains a set of *images* which may be grouped into *collections*.

Courses Endpoints
----------------

- `/courses`  Lists courses
- `/courses/{pk}` Course detail
- `/courses/{pk}/collections` Lists a course's collections
- `/courses/{pk}/images`  Lists a course's images

LTI Attributes
--------------
A course associated with an LTI context must have the following attributes at minimum:

- `lti_context_id` Opaque identifier that uniquely identifies tool context (i.e. Canvas Course)
- `lti_tool_consumer_instance_guid` DNS of the consumer instance that launched the tool

Together, these two attributes should be unique. These attributes should be present in an
LTI launch as `context_id` and `tool_consumer_instance_guid`.

To search for a course associated with an LTI context:

- `/courses?lti_context_id=<context_id>&lti_tool_consumer_instance_guid=<tool_consumer_instance_guid>`

Since one and only one instance of a course can exist with those two attributes, the response should
be an empty list or a list with one object.
    '''
    queryset = Course.objects.prefetch_related('resources', 'collections', 'collections__resources', 'resources__media_store')
    serializer_class = CourseSerializer
    permission_classes = (CourseEndpointPermission,)

    def get_queryset(self):
        queryset = super(CourseViewSet, self).get_queryset()
        queryset = CourseEndpointFilter(self).filter_queryset(queryset)
        return queryset

    def list(self, request, format=None):
        queryset = self.get_queryset()

        # Filter queryset by LTI context params
        lti_params = ('lti_context_id', 'lti_tool_consumer_instance_guid')
        lti_filters = dict([(k, self.request.GET[k]) for k in lti_params if k in self.request.GET])
        if len(lti_filters.keys()) > 0:
            queryset = queryset.filter(**lti_filters)

        serializer = CourseSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, format=None):
        course = self.get_object()
        include = ['images', 'collections']
        serializer = CourseSerializer(course, context={'request': request}, include=include)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def manifests(self, request, pk=None, format=None):
        course = self.get_object()
        manifests = []
        for collection in course.collections.all():
            url = reverse('collection-manifest', kwargs={"pk": collection.pk})
            manifests.append({
                "label": collection.title,
                "url": request.build_absolute_uri(url),
            })
        return Response(manifests)


class CollectionViewSet(viewsets.ModelViewSet):
    '''
A **collection** resource is a grouping of *images*.

Collection Endpoints
----------------

- `/collections`  Lists collections
- `/collections/{pk}` Collection detail
- `/collections/{pk}/images`  Lists a collection's images
    '''
    queryset = Collection.objects.select_related('course').prefetch_related('resources__resource__media_store')
    serializer_class = CollectionSerializer
    permission_classes = (CollectionEndpointPermission,)

    def get_queryset(self):
        queryset = super(CollectionViewSet, self).get_queryset()
        queryset = CollectionEndpointFilter(self).filter_queryset(queryset)
        return queryset

    def list(self, request, format=None):
        collections = self.get_queryset()
        serializer = CollectionSerializer(collections, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, format=None):
        collection = self.get_object()
        include = ['images']
        serializer = CollectionSerializer(collection, context={'request': request}, include=include)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def manifest(self, request, pk=None, format=None):
        collection = self.get_object()
        collection_manifest_controller = CollectionManifestController(request, collection)
        data = collection_manifest_controller.get_data()
        return Response(data)

class CourseCollectionsView(GenericAPIView):
    queryset = Collection.objects.select_related('course').prefetch_related('resources__resource__media_store')
    serializer_class = CollectionSerializer
    permission_classes = (CollectionEndpointPermission,)

    def get(self, request, pk=None, format=None):
        course_pk = pk
        collections = self.get_queryset().filter(course__pk=course_pk).order_by('sort_order')
        include = ['images']
        serializer = CollectionSerializer(collections, many=True, context={'request': request}, include=include)
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        course_pk = pk
        data = request.data.copy()
        course = get_object_or_404(Course, pk=pk)
        data['course_id'] = course.pk
        serializer = CollectionSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseImagesListView(GenericAPIView):
    serializer_class = ResourceSerializer
    queryset = Resource.objects.select_related('course', 'media_store')
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = (ResourceEndpointPermission,)

    def get(self, request, pk=None, format=None):
        course_pk = pk
        images = self.get_queryset().filter(course__pk=course_pk).order_by('sort_order')
        serializer = ResourceSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        course_pk = pk
        course = get_object_or_404(Course, pk=pk)
        file_param = 'file'
        if file_param not in request.FILES:
            raise exceptions.APIException("Error: missing '%s' parameter in upload" % file_param)
        elif len(request.FILES) == 0:
            raise exceptions.APIException("Error: no files uploaded")

        response_data = []
        logger.debug("File uploads: %s" % request.FILES.getlist(file_param))

        files = []
        for file in request.FILES.getlist(file_param):
            if "zip" in file.content_type:
                # unzip and append to the list
                zip = zipfile.ZipFile(file, "r")
                for f in zip.namelist():
                    logger.debug("ZipFile content: %s" % f)
                    zf = zip.open(f).read()
                    newfile = File(io.BytesIO(zf))
                    newfile.name = f

                    # avoiding temp files added to archive
                    if "__MACOSX" not in newfile.name:
                        files.append(newfile)
            else:
                files.append(file)

        for file_upload in files:
            logger.debug("Processing file upload: %s" % file_upload.name)
            data = request.data.copy()
            data['course_id'] = course.pk
            serializer = ResourceSerializer(data=data, context={'request': request}, file_upload=file_upload)
            if serializer.is_valid():
                serializer.save()
                response_data.append(serializer.data)
            else:
                logger.error(serializer.errors)
                return Response(response_data + [serializer.errors], status=status.HTTP_400_BAD_REQUEST)
        return Response(response_data, status=status.HTTP_201_CREATED)

class CollectionImagesListView(GenericAPIView):
    queryset = CollectionResource.objects.select_related('collection', 'resource').prefetch_related('resource__media_store')
    serializer_class = CollectionResourceSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk=None, format=None):
        collection_resources = self.get_queryset().filter(collection__pk=pk).order_by('sort_order')
        serializer = CollectionResourceSerializer(collection_resources, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        collection = get_object_or_404(Collection, pk=pk)
        data = []
        for collection_resource in request.data:
            collection_resource = collection_resource.copy()
            collection_resource['collection_id'] = collection.pk
            data.append(collection_resource)
        serializer = CollectionResourceSerializer(data=data, many=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CollectionImagesDetailView(GenericAPIView):
    queryset = CollectionResource.objects.all()
    serializer_class = CollectionResourceSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk=None, format=None):
         collection_resource = self.get_object()
         serializer = CollectionResourceSerializer(collection_resource, context={'request': request})
         return Response(serializer.data)

    def delete(self, request, pk=None, format=None):
        collection_resource = self.get_object()
        collection_resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CourseImageViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.select_related('course', 'media_store')
    serializer_class = ResourceSerializer
    permission_classes = (ResourceEndpointPermission,)

    def get_queryset(self):
        queryset = super(CourseImageViewSet, self).get_queryset()
        queryset = ResourceEndpointFilter(self).filter_queryset(queryset)
        return queryset
