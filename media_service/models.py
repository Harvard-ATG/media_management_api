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
        verbose_name = 'media_store'
        verbose_name_plural = 'media_stores'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.file_name)
    
    def get_image_server_url(self):
        return 'http://localhost:8000/loris-image-server/%s' % self.pk
    
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

class CourseImage(BaseModel, SortOrderModelMixin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='images')
    media_store = models.ForeignKey(MediaStore, null=True, on_delete=models.SET_NULL)
    is_upload = models.BooleanField(default=True, null=False)
    upload_file_name = models.CharField(max_length=4096, null=True)
    img_type = models.CharField(max_length=128, null=True)
    img_url = models.CharField(max_length=4096, null=True)
    img_width = models.PositiveIntegerField(null=True)
    img_height = models.PositiveIntegerField(null=True)
    thumb_url = models.CharField(max_length=4096, null=True)
    thumb_width = models.PositiveIntegerField(null=True)
    thumb_height = models.PositiveIntegerField(null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(UserProfile, null=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'course_image'
        verbose_name_plural = 'course_images'

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})
        super(CourseImage, self).save(*args, **kwargs)

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)
    

    @classmethod
    def get_course_images(cls, course_pk):
        images = cls.objects.filter(course__pk=course_pk).order_by('sort_order')
        return images
    
class Collection(BaseModel, SortOrderModelMixin):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='collections')
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'collection'
        verbose_name_plural = 'collections'

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})
        super(Collection, self).save(*args, **kwargs)

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)

    @classmethod
    def get_course_collections(cls, course_pk):
        collections = cls.objects.filter(course__pk=course_pk).order_by('sort_order')
        return collections

class CollectionImage(BaseModel, SortOrderModelMixin):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='images')
    course_image = models.ForeignKey(CourseImage, on_delete=models.CASCADE, related_name='collections')
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'collection_image'
        verbose_name_plural = 'collection_images'

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"collection__pk": self.collection.pk})
        super(CollectionImage, self).save(*args, **kwargs)

    def __unicode__(self):
        return "{0}".format(self.id)

    @classmethod
    def get_collection_images(cls, collection_pk):
        images = cls.objects.filter(collection__pk=collection_pk).order_by('sort_order')
        return images
