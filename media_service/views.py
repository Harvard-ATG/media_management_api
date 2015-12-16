from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route, api_view
from rest_framework.reverse import reverse
from media_service.models import Course, Collection, CourseImage, MediaStore, CollectionImage
from media_service.serializers import UserSerializer, CourseSerializer, CourseSerializerWithRelated, CourseImageSerializer, CreateCourseImageSerializer, \
    CollectionSerializer, CollectionSerializerWithRelated, CollectionImageSerializer


class APIRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'courses': reverse('course-list', request=request, format=format),
            'collections': reverse('collection-list', request=request, format=format),
            'images': reverse('image-list', request=request, format=format),
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
        serializer = CourseSerializerWithRelated(course, context={'request': request})
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
        serializer = CollectionSerializerWithRelated(collection, context={'request': request})
        return Response(serializer.data)

class ImageViewSet(viewsets.ModelViewSet):
    queryset = CourseImage.objects.all()
    serializer_class = CourseImageSerializer

class CourseCollectionsView(APIView):
    def get(self, request, pk=None, format=None):
        collections = Collection.get_course_collections(pk)
        serializer = CollectionSerializerWithRelated(collections, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        serializer = CollectionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseImagesView(APIView):
    serializer_class = CourseImageSerializer
    def get(self, request, pk=None, format=None):
        images = CourseImage.get_course_images(pk)
        serializer = CourseImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        data = request.data.copy()
        course = get_object_or_404(Course, pk=pk)
        data['course'] = course.pk
        serializer = CreateCourseImageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CollectionImagesView(APIView):
    serializer_class = CollectionSerializer
    def get(self, request, pk=None, format=None):
        images = CollectionImage.get_collection_images(pk)
        serializer = CollectionSerializerWithRelated(images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        return Response({'error': 'not implemented'})

class ImageUploadView(APIView):
    def post(self, request, pk=None, format=None):
        return Response({'error': 'not implemented'})

    def put(self, request, pk=None, format=None):
        return Response({'error': 'not implemented'})
    