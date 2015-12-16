from django.contrib.auth.models import User, Group
from rest_framework import serializers
from media_service.models import MediaStore, Course, Collection, CollectionImage, CourseImage

def media_store_to_representation(media_store_instance):
    data = {
        "image_type": media_store.file_type,
        "image_width": media_store.img_width,
        "image_height": media_store.img_width,
        "original_url": None,
        "thumb_url": None,
        "thumb_width": None,
        "thumb_height": None,
    }
    return data

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'email', 'groups')

class CollectionImageSerializer(serializers.HyperlinkedModelSerializer):
    collection_id = serializers.PrimaryKeyRelatedField(queryset=Collection.objects.all())
    collection_url = serializers.HyperlinkedIdentityField(view_name="collection-detail", lookup_field="pk")
    course_image_id = serializers.PrimaryKeyRelatedField(queryset=CourseImage.objects.all())
    
    class Meta:
        model = CollectionImage
        fields = ('id', 'collection_url', 'collection_id', 'course_image_id', 'sort_order', 'created', 'updated')

    def create(self, validated_data):
        collection_image = CollectionImage(
            collection=validated_data['collection_id'],
            course_image=validated_data['course_image_id'],
        )
        collection_image.save()
        return collection_image

    def to_representation(self, instance):
        data =  super(CollectionImageSerializer, self).to_representation(instance)
        data['type'] = 'collectionimages'
        data.update({
            "image_id": instance.course_image.id,
            "title": instance.course_image.title,
            "description": instance.course_image.description,
            "original_file_name": instance.course_image.original_file_name,
        })

        if instance.course_image.media_store is None:
            data.update({"image_uploaded": False})
        else:
            media_store = instance.course_image.media_store
            data.update({"image_uploaded": True})
            data.update(media_store_to_representation(media_store))
        return data

class CollectionSerializer(serializers.HyperlinkedModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    images_url = serializers.HyperlinkedIdentityField(view_name="collectionimages-list", lookup_field="pk")

    class Meta:
        model = Collection
        fields = ('url', 'id', 'title', 'description', 'sort_order', 'course_id', 'images_url', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        include = kwargs.pop('include', [])
        super(CollectionSerializer, self).__init__(*args, **kwargs)
        
        if 'images' in include:
            self.fields['images'] = CollectionImageSerializer(many=True, read_only=True)

        self._collection_images = list(CollectionImage.objects.all())

    def to_representation(self, instance):
        data = super(CollectionSerializer, self).to_representation(instance)
        data['type'] = 'collections'
        collection_images = [x for x in self._collection_images if x.collection.pk == instance.pk]
        data['image_ids'] = [x.course_image.pk for x in collection_images]
        return data

class CourseImageSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="image-detail", lookup_field="pk")
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    upload_url = serializers.HyperlinkedIdentityField(view_name="image-upload", lookup_field="pk")

    class Meta:
        model = CourseImage
        fields = ('url', 'upload_url', 'id', 'course_id', 'title', 'description', 'sort_order', 'original_file_name', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        super(CourseImageSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        course_image = CourseImage(
            course=validated_data['course_id'],
            title=validated_data['title'],
            description=validated_data['description']
        )
        course_image.save()
        return course_image

    def to_representation(self, instance):
        data =  super(CourseImageSerializer, self).to_representation(instance)
        data['type'] = 'images'
        if instance.media_store is None:
            data.update({"image_uploaded": False})
        else:
            media_store = instance.media_store
            data.update({"image_uploaded": True})
            data.update(media_store_to_representation(media_store))
        return data

class CourseSerializer(serializers.HyperlinkedModelSerializer):
    collections_url = serializers.HyperlinkedIdentityField(view_name="course-collections", lookup_field="pk")
    images_url = serializers.HyperlinkedIdentityField(view_name="courseimages-list", lookup_field="pk")
    
    class Meta:
        model = Course
        fields = ('url', 'id', 'title', 'lti_context_id', 'collections_url', 'images_url', 'created', 'updated')

    def __init__(self, *args, **kwargs):
        include = kwargs.pop('include', [])
        super(CourseSerializer, self).__init__(*args, **kwargs)

        if 'images' in include:
            self.fields['images'] = CourseImageSerializer(many=True, read_only=True)
        if 'collections' in include:
            self.fields['collections'] = CollectionSerializer(many=True, read_only=True)
            
    def to_representation(self, instance):
        data = super(CourseSerializer, self).to_representation(instance)
        data['type'] = 'courses'
        return data
    
