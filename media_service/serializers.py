from django.contrib.auth.models import User, Group
from rest_framework import serializers
from media_service.models import Course, Collection, CollectionImage, CourseImage

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'email', 'groups')

class CollectionImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CollectionImage
        fields = ('url', 'id', 'course_image', 'sort_order', 'created', 'updated')

class CollectionSerializer(serializers.HyperlinkedModelSerializer):
    course_id = serializers.IntegerField(source="course.pk")
    course_url = serializers.HyperlinkedIdentityField(view_name="course-detail", lookup_field="pk")
    images_url = serializers.HyperlinkedIdentityField(view_name="collection-images", lookup_field="pk")
    class Meta:
        model = Collection
        fields = ('url', 'id', 'title', 'description', 'sort_order', 'course_url', 'course_id', 'images_url', 'created', 'updated')

class CollectionSerializerWithRelated(CollectionSerializer):
    images = CollectionImageSerializer(many=True, read_only=True)
    class Meta:
        model = CollectionSerializer.Meta.model
        fields = CollectionSerializer.Meta.fields + ('images', )

class CourseImageSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="image-detail", lookup_field="pk")
    course_url = serializers.HyperlinkedIdentityField(view_name="course-detail", lookup_field="pk")
    upload_url = serializers.HyperlinkedIdentityField(view_name="image-upload", lookup_field="pk")
    class Meta:
        model = CourseImage
        fields = ('url', 'course_url', 'upload_url', 'id', 'title', 'description', 'sort_order', 'original_file_name', 'created', 'updated')

class CreateCourseImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseImage
        fields = ('id', 'title', 'course', 'description')
    
    def create(self, validated_data):
        course_image = CourseImage(
            course=validated_data['course'],
            title=validated_data['title'],
            description=validated_data['description']
        )
        course_image.save()
        return course_image

class CourseSerializer(serializers.HyperlinkedModelSerializer):
    collections_url = serializers.HyperlinkedIdentityField(view_name="course-collections", lookup_field="pk")
    images_url = serializers.HyperlinkedIdentityField(view_name="course-images", lookup_field="pk")
    class Meta:
        model = Course
        fields = ('url', 'id', 'title', 'lti_context_id', 'collections_url', 'images_url', 'created', 'updated')

class CourseSerializerWithRelated(CourseSerializer):
    collections = CollectionSerializer(many=True, read_only=True)
    images = CourseImageSerializer(many=True, read_only=True)
    class Meta:
        model = CourseSerializer.Meta.model
        fields = CourseSerializer.Meta.fields + ('collections', 'images')