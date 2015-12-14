from django.db import models
from django.db.models import Max
from django.conf import settings

class SortOrderModelMixin(object):
    @classmethod
    def next_sort_order(cls, filters):
        result = cls.objects.filter(**filters).aggregate(n=Max('sort_order'))
        if result['n'] is None:
            return 1
        return result['n'] + 1

class MediaStore(models.Model):
    file_name = models.CharField(max_length=1024, null=False)
    file_size = models.PositiveIntegerField(null=False)
    file_md5hash = models.CharField(max_length=32, null=False)
    file_type = models.CharField(max_length=128, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    reference_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'mediastore'
        verbose_name_plural = 'mediastores'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.file_name)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lti_user_id = models.CharField(max_length=1024, unique=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'user_profile'
        verbose_name_plural = 'user_profiles'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.lti_user_id)

class Course(models.Model):
    title = models.CharField(max_length=255)
    lti_context_id = models.CharField(max_length=255, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'course'
        verbose_name_plural = 'courses'
        ordering = ["title"]

    def __unicode__(self):
        return "{0}:{1}:{2}".format(self.id, self.lti_context_id, self.title)

class Collection(models.Model, SortOrderModelMixin):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})
        super(Collection, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'collection'
        verbose_name_plural = 'collections'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)

class CollectionItem(models.Model, SortOrderModelMixin):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    media_file = models.ForeignKey(MediaStore, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"collection__pk": self.collection.pk})
        super(CollectionItem, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'collectionitem'
        verbose_name_plural = 'collectionitems'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)
