from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status, exceptions
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route, api_view
from rest_framework.reverse import reverse
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser, FileUploadParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied

from media_service.models import Course, Collection, Resource, MediaStore, CollectionResource
from media_service.mediastore import MediaStoreUpload, processFileUploads, processRemoteImages
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

Endpoints
----------------

- `/collections`
- `/collections/{pk}`

Methods
-------

- `get /collections`  Lists collections
- `post /collections` Creates new collection
- `get /collections/{pk}` Retrieves collection details
- `put /collections/{pk}` Updates collection
- `delete /collections/{pk}` Deletes a collection
- `get /collections/{pk}/images`  Lists a collection's images
- `get /collections/{pk}/manifest` Collection IIIF manifest of images
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
    '''
A **course collections** resource is a set of *collections* that belong to a *course*.

Endpoints
----------------

- `/courses/{pk}/collections`

Methods
-------

- `GET /courses/{pk}/collections`  Lists collections that belong to the course
- `POST /courses/{pk}/collections` Creates a new collection and adds it to the course
- `PUT /courses/{pk}/collections`  Updates collections

Details
-------

### Updating the order of collections in one batch

Provide an array of collection IDs:

    PUT /courses/{pk}/collections
    {
	    "sort_order": [1,7,6,5,3,2]
    }

### Updating the details of collections in one batch

Provide an array of items, which are just collection objects:

    PUT /courses/{pk}/collections
    {
        "items": [{
            "id": 1,
            "title": "Collection #1",
            "description": "Foo",
            "sort_order": 1
        }, {
            "id": 2,
            "title": "Collection #2",
            "description": "Bar",
            "sort_order": 2
        }]
    }

    '''
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

    def put(self, request, pk=None, format=None):
        course_pk = pk
        collections = self.get_queryset().filter(course__pk=course_pk).order_by('sort_order')
        collection_ids = [c.pk for c in collections]
        collection_map = dict([(c.pk, c) for c in collections])
        data = request.data.copy()

        # Shortcut to just update the order of collections
        if 'sort_order' in data:
            if not (set(collection_ids) == set(data['sort_order'])):
                mismatch = list(set(collection_ids) - set(data['sort_order']))
                raise exceptions.APIException("Error updating sort order. Missing or invalid collection IDs. Set mismatch: %s" % mismatch)
            with transaction.atomic():
                for index, collection_id in enumerate(data['sort_order'], start=1):
                    collection = collection_map[collection_id]
                    collection.sort_order = index
                    collection.save()
                    logger.debug("Updated collection=%s sort_order=%s" % (collection.pk, collection.sort_order))
            return Response({"message": "Sort order updated", "data": data['sort_order'] })

        # Update a batch of collections
        elif 'items' in data:
            for item in data['items']:
                if 'id' not in item:
                    raise exceptions.APIException("Error updating collections. Collection missing collection primary key 'id'. Given: %s" % item)

            item_ids = [item['id'] for item in data['items']]
            if not (set(item_ids) <= set(collection_ids)):
                raise exceptions.APIException("Error updating collections. Given collection items MUT be a subset of the course collections.")

            logger.debug("Updating collections: %s" % item_ids)
            serializer_data = []
            for item in data['items']:
                collection_instance = collection_map[item['id']]
                serializer = CollectionSerializer(collection_instance, data=item, context={'request': request})
                serializer.is_valid(raise_exception=True)
                serializer.save()
                serializer_data.append(serializer.data)
            return Response(serializer_data)

        raise exceptions.APIException("Must specify one of 'items' or 'sort_order' to update a batch of collections for course %s." % course_pk)


class CourseImagesListView(GenericAPIView):
    '''
A **course images** resource is a set of *images* that belong to a *course*.
This is also referred to as the course's image library.

Endpoints
----------------

- `/courses/{pk}/images`

Methods
-------

- `get /courses/{pk}/images`  Lists images that belong to the course
- `post /courses/{pk}/images` Uploads an image to the course
    '''
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
        logger.debug("request content_type=%s data=%s" % (request.content_type, request.data))
        request_data = request.data.copy()
        course = get_object_or_404(Course, pk=pk)
        request_data['course_id'] = course.pk
        files = []
        response_data = []
        serializers = []

        # Handle images uploaded directly
        if request.content_type.startswith("multipart/form-data"):
            file_param = 'file'
            if file_param not in request.FILES:
                raise exceptions.APIException("Error: missing '%s' parameter in upload" % file_param)
            elif len(request.FILES) == 0:
                raise exceptions.APIException("Error: no files uploaded")
            logger.debug("File uploads: %s" % request.FILES.getlist(file_param))
            processed_uploads = processFileUploads(request.FILES.getlist(file_param))
            for index, f in processed_uploads.iteritems():
                data = request_data.copy()
                logger.debug("Processing file upload: %s" % f.name)
                serializer = ResourceSerializer(data=data, context={'request': request}, is_upload=True, file_object=f)
                serializers.append(serializer)

        # Handle import of images by URL, provided in a JSON message
        elif request.content_type.startswith("application/json"):
            logger.debug("Request data: %s" % request_data)
            MAX_IMAGE_ITEMS = 10 # max number of item urls that we will import at a time
            if 'items' not in request_data or not isinstance(request_data['items'], list):
                raise exceptions.APIException("Error: missing 'items' parameter for JSON upload")
            elif len(request_data['items']) == 0:
                raise exceptions.APIException("Error: empty image items")
            elif len(request_data['items']) > MAX_IMAGE_ITEMS:
                raise exceptions.APIException("Error: exceeded maximum number of image items (max=%d)." % MAX_IMAGE_ITEMS)
            try:
                processed_items = processRemoteImages(request_data['items'])
            except Exception as e:
                raise exceptions.APIException(str(e))

            for url, item in processed_items.iteritems():
                f = item['file']
                data = item['data'].copy()
                data['course_id'] = course.pk
                logger.debug("Processing image url=%s file=%s data=%s" % (url, f.name, data))
                serializer = ResourceSerializer(data=data, context={'request': request}, is_upload=False, file_object=f, file_url=url)
                serializers.append(serializer)
        else:
            raise exceptions.APIException("Error: content type '%s' not supported" % request.content_type)

        # Complete the process by serializing the resources
        for serializer in serializers:
            if serializer.is_valid():
                serializer.save()
                response_data.append(serializer.data)
            else:
                logger.error(serializer.errors)
                return Response(response_data + [serializer.errors], status=status.HTTP_400_BAD_REQUEST)
        return Response(response_data, status=status.HTTP_201_CREATED)

class CollectionImagesListView(GenericAPIView):
    '''
A **collection images** resource is a set of *images* that are associated with a *collection*.

Endpoints
----------------

- `/collections/{pk}/images`

Methods
-------

- `get /courses/{pk}/images`  Lists images that belong to the course
- `post /courses/{pk}/images` Adds images to the collection that already exist in the course library.
    '''
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
    '''
A **collection images detail** resource describes an image that has been associated with a collection.

Endpoints
----------------

- `collection-images/{pk}`

Methods
-------

- `get /collection-images/{pk}` Retrieves details of image associated with collection
- `delete /collection-images/{pk}` Removes the image from the collection
    '''
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
    '''
A **course images** resource is a set of *images* that are associated with a *collection*.

Endpoints
----------------

- `/images`
- `/images/{pk}`

Methods
-------

- `get /images`  Lists images
- `get /images/{pk}` Retrieves details of an image
    '''
    queryset = Resource.objects.select_related('course', 'media_store')
    serializer_class = ResourceSerializer
    permission_classes = (ResourceEndpointPermission,)

    def get_queryset(self):
        queryset = super(CourseImageViewSet, self).get_queryset()
        queryset = ResourceEndpointFilter(self).filter_queryset(queryset)
        return queryset
