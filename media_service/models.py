from django.db import models
from django.db.models import Max
from django.conf import settings

class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class SortOrderModelMixin(object):
    @classmethod
    def next_sort_order(self, filters=None):
        '''
        Returns the next available sort order for the given set of filters.
        '''
        if filters is None:
            objects = self.objects.all()
        else:
            objects = self.objects.filter(**filters)
        result = objects.aggregate(n=Max('sort_order'))
        if result['n'] is None:
            return 1
        return result['n'] + 1

class MediaStore(BaseModel):
    file_name = models.CharField(max_length=1024, null=False)
    file_size = models.PositiveIntegerField(null=False)
    file_md5hash = models.CharField(max_length=32, null=False)
    img_type = models.CharField(max_length=128, null=True)
    img_width = models.PositiveIntegerField(null=True)
    img_height = models.PositiveIntegerField(null=True)
    reference_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'mediastore'
        verbose_name_plural = 'mediastores'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.file_name)

class UserProfile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lti_user_id = models.CharField(max_length=1024, unique=True, blank=True)

    class Meta:
        verbose_name = 'user_profile'
        verbose_name_plural = 'user_profiles'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.lti_user_id)

class Course(BaseModel):
    title = models.CharField(max_length=255)
    lti_context_id = models.CharField(max_length=255, blank=False)

    class Meta:
        verbose_name = 'course'
        verbose_name_plural = 'courses'
        ordering = ["title"]

    def __unicode__(self):
        return "{0}:{1}:{2}".format(self.id, self.lti_context_id, self.title)

class CourseMedia(BaseModel, SortOrderModelMixin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    media_file = models.ForeignKey(MediaStore, null=True, on_delete=models.SET_NULL)
    original_file_name = models.CharField(max_length=4096, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(UserProfile, null=True)
    sort_order = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})
        super(CourseMedia, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'course_media'
        verbose_name_plural = 'course_media'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)

class Collection(BaseModel, SortOrderModelMixin):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})
        super(Collection, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'collection'
        verbose_name_plural = 'collections'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)

class CollectionItem(BaseModel, SortOrderModelMixin):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    course_media = models.ForeignKey(CourseMedia, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"collection__pk": self.collection.pk})
        super(CollectionItem, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'collection_item'
        verbose_name_plural = 'collection_items'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)
