from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route, api_view
from rest_framework.reverse import reverse
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser, FileUploadParser
from media_service.models import Course, Collection, CourseImage, MediaStore, CollectionImage
from media_service.serializers import UserSerializer, CourseSerializer, CourseImageSerializer, \
    CollectionSerializer, CollectionImageSerializer


class APIRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'courses': reverse('course-list', request=request, format=format),
            'collections': reverse('collection-list', request=request, format=format),
            'course-images': reverse('courseimage-list', request=request, format=format),
        })

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    
    def list(self, request, format=None):
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, lti_context=None, pk=None, format=None):
        if lti_context is None:
            course = get_object_or_404(Course, pk=pk)
        else:
            course = get_object_or_404(Course, lti_context_id=pk)
        include = ['images', 'collections']
        serializer = CourseSerializer(course, context={'request': request}, include=include)
        return Response(serializer.data)

class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    
    def list(self, request, format=None):
        collections = Collection.objects.all()
        serializer = CollectionSerializer(collections, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, format=None):
        collection = get_object_or_404(Collection, pk=pk)
        include = ['images']
        serializer = CollectionSerializer(collection, context={'request': request}, include=include)
        return Response(serializer.data)

class CourseImageViewSet(viewsets.ModelViewSet):
    queryset = CourseImage.objects.all()
    serializer_class = CourseImageSerializer

def get_course_pk(lti_context, pk):
    if lti_context is None:
        course_pk = pk
    else:
        course = get_object_or_404(Course, lti_context_id=pk)
        course_pk = course.pk
    return course_pk

class CourseCollectionsView(APIView):
    serializer_class = CollectionSerializer
    def get(self, request, lti_context=None, pk=None, format=None):
        course_pk = get_course_pk(lti_context, pk)
        collections = Collection.get_course_collections(course_pk)
        include = ['images']
        serializer = CollectionSerializer(collections, many=True, context={'request': request}, include=include)
        return Response(serializer.data)

    def post(self, request, lti_context=None, pk=None, format=None):
        course_pk = get_course_pk(lti_context, pk)
        data = request.data.copy()
        course = get_object_or_404(Course, pk=pk)
        data['course_id'] = course.pk
        serializer = CollectionSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseImagesListView(APIView):
    serializer_class = CourseImageSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    def get(self, request, lti_context=None, pk=None, format=None):
        course_pk = get_course_pk(lti_context, pk)
        images = CourseImage.get_course_images(course_pk)
        serializer = CourseImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, lti_context=None, pk=None, format=None):
        course_pk = get_course_pk(lti_context, pk)
        course = get_object_or_404(Course, pk=pk)
        data = request.data.copy()
        data['course_id'] = course.pk
        serializer = CourseImageSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CollectionImagesListView(APIView):
    serializer_class = CollectionImageSerializer
    def get(self, request, pk=None, format=None):
        collection_images = CollectionImage.get_collection_images(pk)
        serializer = CollectionImageSerializer(collection_images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        collection = get_object_or_404(Collection, pk=pk)
        data = []
        for collection_image in request.data:
            item = collection_image.copy()
            item['collection_id'] = collection.pk
            data.append(item)
        serializer = CollectionImageSerializer(data=data, many=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CollectionImagesDetailView(APIView):
    serializer_class = CollectionImageSerializer
    def get(self, request, pk=None, format=None):
         collection_image = get_object_or_404(CollectionImage, pk=pk)
         serializer = CollectionImageSerializer(collection_image, context={'request': request})
         return Response(serializer.data)
    
    def delete(self, request, pk=None, format=None):
        collection_image = get_object_or_404(CollectionImage, pk=pk)
        collection_image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CourseImageUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    def post(self, request, pk=None, format=None):
        instance = get_object_or_404(CourseImage, pk=pk)
        data = request.data
        serializer = CourseImageSerializer(data=data, instance=instance, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    