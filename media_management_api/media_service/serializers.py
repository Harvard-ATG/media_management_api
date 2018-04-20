from django.contrib.auth.models import User, Group
from rest_framework import serializers, exceptions
from rest_framework.reverse import reverse
from .models import Course, Collection, CollectionResource, Resource
from . import mediastore
import json

def resource_to_representation(resource):
    return resource.get_representation()

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'email', 'groups')

class CollectionResourceSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="api:collectionimages-detail", lookup_field="pk")
    collection_id = serializers.PrimaryKeyRelatedField(queryset=Collection.objects.all())
    collection_url = serializers.HyperlinkedRelatedField(view_name="api:collection-detail", lookup_field="collection_id", lookup_url_kwarg="pk", read_only=True)
    course_image_id = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all(), source='resource_id')

    class Meta:
        model = CollectionResource
        fields = ('id', 'url', 'collection_url', 'collection_id', 'course_image_id', 'sort_order', 'created', 'updated')

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
            "url": reverse('api:collectionimages-detail', kwargs={'pk': instance.pk}, request=self.context['request']),
            "course_image_id": resource.id,
            "title": resource.title,
            "description": resource.description,
            "original_file_name": resource.original_file_name,
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
    url = serializers.HyperlinkedIdentityField(view_name="api:collection-detail", lookup_field="pk")
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    images_url = serializers.HyperlinkedIdentityField(view_name="api:collectionimages-list", lookup_field="pk")
    description = serializers.CharField(max_length=None, required=False, allow_blank=True)
    course_image_ids = CollectionResourceIdsField(read_only=False, required=False)
    custom_iiif_manifest_url = serializers.CharField(max_length=4096, required=False, allow_blank=True)

    class Meta:
        model = Collection
        fields = (
            'url',
            'id',
            'title',
            'description',
            'sort_order',
            'course_id',
            'course_image_ids',
            'images_url',
            'custom_iiif_manifest_url',
            'created',
            'updated',
        )

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
            custom_iiif_manifest_url=validated_data.get('custom_iiif_manifest_url', '')
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
        if 'sort_order' in validated_data:
            instance.sort_order = validated_data['sort_order']
        if 'custom_iiif_manifest_url' in validated_data:
            instance.custom_iiif_manifest_url = validated_data['custom_iiif_manifest_url']
        if 'course_image_ids' in validated_data:
            course_image_ids = validated_data['course_image_ids']
            CollectionResource.objects.filter(collection__pk=instance.pk).delete()
            for course_image_id in course_image_ids:
                CollectionResource.objects.create(collection_id=instance.pk, resource_id=course_image_id)
        instance.save()
        return Collection.objects.get(pk=instance.pk) # Get object fresh from DB to avoid cache problems

    def to_representation(self, instance):
        data = super(CollectionSerializer, self).to_representation(instance)
        request = self.context['request']
        data['type'] = 'collections'
        data['default_iiif_manifest_url'] = request.build_absolute_uri(reverse('api:iiif:manifest', kwargs={'manifest_id': instance.pk}))
        return data

def metadata_validator(value):
    '''
    This validator ensures that the metadata is a list of dicts like this:

        [ {"label": "foo", "value": "bar"}, ... ]

    Otherwise it will raise a ValidationError().
    '''

    metadata = value
    if metadata is not None:
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
    url = serializers.HyperlinkedIdentityField(view_name="api:image-detail", lookup_field="pk")
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    description = serializers.CharField(max_length=None, required=False, allow_blank=True)
    metadata = serializers.JSONField(binary=False, required=False, allow_null=True, validators=[metadata_validator])

    class Meta:
        model = Resource
        fields = ('url', 'id', 'course_id', 'title', 'description', 'metadata', 'sort_order', 'original_file_name', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        self.is_upload = kwargs.pop('is_upload', None)
        self.file_object = kwargs.pop('file_object', None)
        self.file_url = kwargs.pop('file_url', None)
        super(ResourceSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        request = self.context['request']
        course_id = validated_data['course_id']
        title = validated_data.get('title', '')
        description = validated_data.get('description', '')
        metadata = validated_data.get('metadata', None)

        media_store_instance = None
        if self.file_object:
            media_store_instance = self.handle_file_object()

        original_file_name = ''
        if self.is_upload:
            title = original_file_name = self.file_object.name
        elif self.file_url:
            original_file_name = self.file_url

        resource_attrs = {
            "course": course_id,
            "title": title,
            "description": description,
            "owner": request.user.profile,
            "media_store": media_store_instance,
            "original_file_name": original_file_name,
            "is_upload": self.is_upload,
        }

        # Metadata cannot be null, so only include if it's non-null
        if metadata is not None:
            resource_attrs['metadata'] = json.dumps(metadata)

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

    def handle_file_object(self):
        '''Uploads file object to the media store.'''
        try:
            media_store_upload = mediastore.MediaStoreUpload(self.file_object)
            media_store_upload.raise_for_error()
            media_store_upload.validate()
        except mediastore.MediaStoreException as e:
            raise exceptions.APIException(str(e))
        media_store_instance = media_store_upload.save()
        return media_store_instance

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
    url = serializers.HyperlinkedIdentityField(view_name="api:course-detail", lookup_field="pk")
    collections_url = serializers.HyperlinkedIdentityField(view_name="api:course-collections", lookup_field="pk")
    images_url = serializers.HyperlinkedIdentityField(view_name="api:course-images", lookup_field="pk")

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
