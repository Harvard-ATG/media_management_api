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
        print "lit_context = %s pk = %s" % (lti_context, pk)
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
        serializer = CollectionSerializerWithRelated(collections, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, lti_context=None, pk=None, format=None):
        course_pk = get_course_pk(lti_context, pk)
        serializer = CollectionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseImagesView(APIView):
    serializer_class = CourseImageSerializer
    def get(self, request, lti_context=None, pk=None, format=None):
        course_pk = get_course_pk(lti_context, pk)
        images = CourseImage.get_course_images(course_pk)
        serializer = CourseImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, lti_context=None, pk=None, format=None):
        course_pk = get_course_pk(lti_context, pk)
        course = get_object_or_404(Course, pk=pk)
        data = request.data.copy()
        data['course'] = course.pk
        serializer = CreateCourseImageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CollectionImagesView(APIView):
    serializer_class = CollectionImageSerializer
    def get(self, request, pk=None, format=None):
        collection_images = CollectionImage.get_collection_images(pk)
        serializer = CollectionImageSerializer(collection_images, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        from django.forms.models import model_to_dict
        collection = get_object_or_404(Collection, pk=pk)
        data = request.data.copy()
        data['collection_id'] = collection.pk
        serializer = CollectionImageSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ImageUploadView(APIView):
    def post(self, request, pk=None, format=None):
        return Response({'error': 'not implemented'})

    def put(self, request, pk=None, format=None):
        return Response({'error': 'not implemented'})
    