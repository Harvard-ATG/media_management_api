from django.contrib.auth.models import User, Group
from rest_framework import serializers
from media_service.models import Course, Collection, CollectionItem

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'id', 'name')

class CourseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Course
        fields = ('url', 'title', 'lti_context_id', 'created', 'updated')

class CollectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Collection
        fields = ('url', 'title', 'description', 'sort_order', 'course', 'created', 'updated')

class CollectionItemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CollectionItem
        fields = ('url', 'title', 'description', 'sort_order', 'collection', 'media_file', 'created', 'updated')