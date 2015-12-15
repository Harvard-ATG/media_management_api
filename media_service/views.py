from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib.auth.models import User, Group
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route
from rest_framework.reverse import reverse
from media_service.models import Course, Collection, CourseImage, MediaStore, CollectionImage
from media_service.serializers import UserSerializer, CourseSerializer, CourseSerializerWithRelated, CourseImageSerializer, \
    CollectionSerializer, CollectionSerializerWithRelated, CollectionImageSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

class CourseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for course views.
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    
    def list(self, request):
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        course = Course.objects.get(pk=pk)
        serializer = CourseSerializerWithRelated(course, context={'request': request})
        return Response(serializer.data)

    @detail_route(methods=['GET', 'POST'])
    def collections(self, request, pk=None):
        if request.method == 'GET':
            collections = Collection.get_course_collections(pk)
            serializer = CollectionSerializerWithRelated(collections, many=True, context={'request': request})
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = CollectionSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['GET', 'PUT', 'POST'])
    def images(self, request, pk=None):
        if request.method == 'GET':
            images = CourseImage.get_course_images(pk)
            serializer = CourseImageSerializer(images, many=True, context={'request': request})
            return Response(serializer.data)
        elif request.method in ('PUT', 'POST'):
            return Response({'error': 'not implemented'})
    
class CollectionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for collection views.
    """
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    
    def list(self, request):
        collections = Collection.objects.all()
        serializer = CollectionSerializer(collections, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        collection = Collection.objects.get(pk=pk)
        serializer = CollectionSerializerWithRelated(collection, context={'request': request})
        return Response(serializer.data)

    @detail_route(methods=['GET', 'POST'])
    def images(self, request, pk=None):
        if request.method == 'GET':
            images = CollectionImage.get_collection_images(pk)
            serializer = CollectionSerializerWithRelated(images, many=True, context={'request': request})
            return Response(serializer.data)
        elif request.method == 'POST':
            return Response({'error': 'not implemented'})
    
class CourseImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for collection views.
    """
    queryset = CourseImage.objects.all()
    serializer_class = CourseImageSerializer
