from django.contrib.auth.models import User, Group
from rest_framework import serializers, exceptions
from rest_framework.reverse import reverse
from media_service.models import MediaStore, Course, Collection, CollectionResource, Resource
from media_service.mediastore import MediaStoreUpload
import json

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
            resource=validated_data['resource_id'],
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
        valid_resource_ids = Resource.objects.filter(pk__in=data).distinct().values_list('pk', flat=True)
        diff = list(set(data).difference(valid_resource_ids))
        if len(diff) != 0:
            raise serializers.ValidationError("Invalid course_image_ids for course %s. Invalid: %s Valid: %s." % (course_pk, diff, valid_resource_ids))
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
        if 'course_image_ids' in validated_data:
            course_image_ids = validated_data['course_image_ids']
            CollectionResource.objects.filter(collection__pk=collection.pk).delete()
            for course_image_id in course_image_ids:
                CollectionResource.objects.create(collection_id=collection.pk, resource_id=course_image_id)
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

def metadata_validator(value):
    '''
    This validator ensures that the metadata is a list of dicts like this:

        [ {"label": "foo", "value": "bar"}, ... ]

    Otherwise it will raise a ValidationError().
    '''

    metadata = value
    if not isinstance(metadata, list):
        raise serializers.ValidationError("Metadata must be a *list* of pairs: [{'label': '', 'value': ''}, ...]. Given: %s" % type(metadata))

    required_fields = ('label', 'value')
    for pair in metadata:
        if not isinstance(pair, dict):
            raise serializers.ValidationError("Metadata pair '%s' invalid. Must be a *dict*: {'label': '', 'value': ''}" % pair)
        if set(pair.keys()) != set(required_fields):
            raise serializers.ValidationError("Metadata pair '%s' invalid. Must contain keys: label, value" % pair)
        if not isinstance(pair['label'], basestring) or not isinstance(pair['value'], basestring):
            raise serializers.ValidationError("Metadata pair '%s' invalid. Label and value must be strings, not composite types." % pair)

class ResourceSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="image-detail", lookup_field="pk")
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    description = serializers.CharField(max_length=None, required=False, allow_blank=True)
    metadata = serializers.JSONField(binary=False, required=False, validators=[metadata_validator])

    class Meta:
        model = Resource
        fields = ('url', 'id', 'course_id', 'title', 'description', 'metadata', 'sort_order', 'upload_file_name', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        self.file_upload = kwargs.pop('file_upload', None)
        super(ResourceSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        course_id = validated_data['course_id']
        title = validated_data['title']
        description = validated_data.get('description', '')
        metadata = validated_data.get('metadata', None)

        upload_result = self.handle_file_upload()
        if 'upload_file_name' in upload_result:
            title = upload_result['upload_file_name']
        resource_attrs = {
            "course": course_id,
            "title": title,
            "description": description,
            "metadata": json.dumps(metadata),
            "media_store": upload_result['media_store'],
            "upload_file_name": upload_result['upload_file_name'],
            "is_upload": upload_result['is_upload'],
        }
        resource = Resource(**resource_attrs)
        resource.save()
        return resource

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.sort_order = validated_data.get('sort_order', instance.sort_order)
        if 'metadata' in validated_data:
            instance.metadata = json.dumps(validated_data['metadata'])
        instance.save()
        return instance

    def handle_file_upload(self):
        if not self.file_upload:
            return {}

        media_store_upload = MediaStoreUpload(self.file_upload)
        if not media_store_upload.isValid():
            raise exceptions.ValidationError("Failed to upload file '%s'. Error: %s" % (self.file_upload.name, media_store_upload.getErrors()))

        media_store_instance = media_store_upload.save()
        result = {
            'media_store': media_store_instance,
            'is_upload': True,
            'upload_file_name': self.file_upload.name,
        }
        return result

    def to_representation(self, instance):
        data =  super(ResourceSerializer, self).to_representation(instance)
        data.update({
            "type": "images",
            "is_upload": instance.is_upload,
            "metadata": instance.load_metadata(),
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
