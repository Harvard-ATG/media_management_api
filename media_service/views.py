from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route, api_view
from rest_framework.reverse import reverse
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser, FileUploadParser
from media_service.models import Course, Collection, Resource, MediaStore, CollectionResource
from media_service.serializers import UserSerializer, CourseSerializer, ResourceSerializer, \
    CollectionSerializer, CollectionResourceSerializer
from media_service.iiif import CollectionManifestController

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
    queryset = Course.objects.prefetch_related('resources', 'collections', 'collections__resources')
    serializer_class = CourseSerializer
    
    def _get_lti_search_filters(self, request):
        lti_search = {}
        for k in ['lti_context_id', 'lti_tool_consumer_instance_guid']:
            if k in request.GET:
                lti_search[k] = request.GET[k]
        return lti_search
    
    def list(self, request, format=None):
        lti_search = self._get_lti_search_filters(request)
        if len(lti_search.keys()) > 0:
            courses = self.get_queryset().filter(**lti_search)
        else:
            courses = self.get_queryset()
        serializer = CourseSerializer(courses, many=True, context={'request': request})
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
    queryset = Collection.objects.select_related('course').prefetch_related('resources__resource')
    serializer_class = CollectionSerializer
    
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

class CourseCollectionsView(APIView):
    serializer_class = CollectionSerializer
    def get(self, request, pk=None, format=None):
        course_pk = pk
        collections = Collection.get_course_collections(course_pk)
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

class CourseImagesListView(APIView):
    serializer_class = ResourceSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    def get(self, request, pk=None, format=None):
        course_pk = pk
        images = Resource.get_course_images(course_pk)
        serializer = ResourceSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        course_pk = pk
        course = get_object_or_404(Course, pk=pk)
        data = request.data.copy()
        data['course_id'] = course.pk
        serializer = ResourceSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CollectionImagesListView(APIView):
    serializer_class = CollectionResourceSerializer
    def get(self, request, pk=None, format=None):
        collection_resources = CollectionResource.get_collection_images(pk)
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

class CollectionImagesDetailView(APIView):
    serializer_class = CollectionResourceSerializer
    def get(self, request, pk=None, format=None):
         collection_resource = get_object_or_404(CollectionResource, pk=pk)
         serializer = CollectionResourceSerializer(collection_resource, context={'request': request})
         return Response(serializer.data)
    
    def delete(self, request, pk=None, format=None):
        collection_resource = get_object_or_404(CollectionResource, pk=pk)
        collection_resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CourseImageUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    def post(self, request, pk=None, format=None):
        instance = get_object_or_404(Resource, pk=pk)
        data = request.data.copy()
        data['course_id'] = instance.course.pk
        serializer = ResourceSerializer(data=data, instance=instance, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseImageViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
