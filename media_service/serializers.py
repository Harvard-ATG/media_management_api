from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework.reverse import reverse
from media_service.models import MediaStore, Course, Collection, CollectionResource, Resource
from media_service.mediastore import MediaStoreUpload

def resource_to_representation(resource):
    return resource.get_representation()

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'email', 'groups')

class CollectionResourceSerializer(serializers.HyperlinkedModelSerializer):
    collection_id = serializers.PrimaryKeyRelatedField(queryset=Collection.objects.all())
    collection_url = serializers.HyperlinkedIdentityField(view_name="collection-detail", lookup_field="pk")
    course_image_id = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all(), source='resource_id')
    
    class Meta:
        model = CollectionResource
        fields = ('id', 'collection_url', 'collection_id', 'course_image_id', 'sort_order', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        super(CollectionResourceSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        collection_resource = CollectionResource(
            collection=validated_data['collection_id'],
            resource=validated_data['course_image_id'],
        )
        collection_resource.save()
        return collection_resource

    def to_representation(self, instance):
        data =  super(CollectionResourceSerializer, self).to_representation(instance)
        resource = instance.resource
        data.update({
            "type": 'collectionimages',
            "url": reverse('collectionimages-detail', kwargs={'pk': instance.pk}, request=self.context['request']),
            "course_image_id": resource.id,
            "title": resource.title,
            "description": resource.description,
            "upload_file_name": resource.upload_file_name,
            "is_upload": resource.is_upload,
        })
        data.update(resource_to_representation(resource))
        return data

class CollectionResourceIdsField(serializers.Field):
    def to_representation(self, obj):
        course_image_ids = [item.resource_id for item in obj.resources.all()]
        return course_image_ids

    def to_internal_value(self, data):
        course_pk = self.parent.instance.course.pk
        found = Resource.objects.filter(course__pk=course_pk, pk__in=data).distinct().values_list('pk', flat=True)
        diff = list(set(data).difference(found))
        if len(diff) != 0:
            raise serializers.ValidationError("Invalid course_image_ids for course %s. Invalid: %s Valid: %s." % (course_pk, diff, found))
        return data

    def get_attribute(self, obj):
        return obj

class CollectionSerializer(serializers.HyperlinkedModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    images_url = serializers.HyperlinkedIdentityField(view_name="collectionimages-list", lookup_field="pk")
    description = serializers.CharField(max_length=None, required=False)
    course_image_ids = CollectionResourceIdsField(read_only=False, required=False)

    class Meta:
        model = Collection
        fields = ('url', 'id', 'title', 'description', 'sort_order', 'course_id', 'course_image_ids', 'images_url', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        include = kwargs.pop('include', [])
        super(CollectionSerializer, self).__init__(*args, **kwargs)
        if 'images' in include:
            self.fields['images'] = CollectionResourceSerializer(source="resources", many=True, read_only=True)

    def create(self, validated_data):
        collection = Collection(
            title=validated_data['title'],
            course=validated_data['course_id'],
            description=validated_data.get('description', ''),
        )
        collection.save()
        return collection
    
    def update(self, instance, validated_data):
        request = self.context['request']
        if not validated_data:
            return instance
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'description' in validated_data:
            instance.description = validated_data['description']
        if 'course_image_ids' in validated_data:
            course_image_ids = validated_data['course_image_ids']
            CollectionResource.objects.filter(collection__pk=instance.pk).delete()
            for course_image_id in course_image_ids:
                CollectionResource.objects.create(collection_id=instance.pk, resource_id=course_image_id)
        instance.save()
        return Collection.objects.get(pk=instance.pk) # Get object fresh from DB to avoid cache problems

    def to_representation(self, instance):
        data = super(CollectionSerializer, self).to_representation(instance)
        data['type'] = 'collections'
        return data

class ResourceSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="image-detail", lookup_field="pk")
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    upload_url = serializers.HyperlinkedIdentityField(view_name="image-upload", lookup_field="pk")
    description = serializers.CharField(max_length=None, required=False)

    class Meta:
        model = Resource
        fields = ('url', 'upload_url', 'id', 'course_id', 'title', 'description', 'sort_order', 'upload_file_name', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        super(ResourceSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        request = self.context['request']
        result = self.handle_file_upload(request)
        resource_attrs = {
            "course": validated_data['course_id'],
            "title": validated_data['title'],
            "description": validated_data.get('description', ''),
            "media_store": result['media_store'],
            "upload_file_name": result['upload_file_name'],
        }

        resource = Resource(**resource_attrs)
        resource.save()

        return resource

    def update(self, instance, validated_data):
        request = self.context['request']
        result = self.handle_file_upload(request)
        instance.media_store = result['media_store']
        instance.upload_file_name = result['upload_file_name']
        instance.is_upload = result['is_upload']
        instance.save()
        return instance

    def handle_file_upload(self, request):
        result = {
            "is_upload": False,
            "media_store": None,
            "upload_file_name": None,
        }
        if 'upload' in request.FILES:
            uploaded_file = request.FILES['upload']
            result['upload_file_name'] = uploaded_file.name
            result['is_upload'] = True
            media_store_upload = MediaStoreUpload(uploaded_file)
            if media_store_upload.is_valid():
                result['media_store'] = media_store_upload.save()
        return result

    def to_representation(self, instance):
        data =  super(ResourceSerializer, self).to_representation(instance)
        data.update({
            "type": "images",
            "is_upload": instance.is_upload,
        })
        data.update(resource_to_representation(instance))
        return data

class CourseSerializer(serializers.HyperlinkedModelSerializer):
    collections_url = serializers.HyperlinkedIdentityField(view_name="course-collections", lookup_field="pk")
    images_url = serializers.HyperlinkedIdentityField(view_name="course-images", lookup_field="pk")
    
    class Meta:
        model = Course
        fields = ('url', 'id', 'title', 'collections_url', 'images_url', 'lti_context_id', 'lti_tool_consumer_instance_guid', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        include = kwargs.pop('include', [])
        super(CourseSerializer, self).__init__(*args, **kwargs)

        if 'images' in include:
            self.fields['images'] = ResourceSerializer(source="resources", many=True, read_only=True)
        if 'collections' in include:
            self.fields['collections'] = CollectionSerializer(many=True, read_only=True)
            
    def to_representation(self, instance):
        data = super(CourseSerializer, self).to_representation(instance)
        data['type'] = 'courses'
        return data
