from django.db import models
from django.db.models import Max
from django.conf import settings
import urllib

# Required settings
IIIF_IMAGE_SERVER_URL = settings.IIIF_IMAGE_SERVER_URL
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_S3_KEY_PREFIX = settings.AWS_S3_KEY_PREFIX

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
    file_extension = models.CharField(max_length=6, null=True)
    file_type = models.CharField(max_length=512, null=True)
    img_width = models.PositiveIntegerField(null=True)
    img_height = models.PositiveIntegerField(null=True)
    reference_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'media_store'
        verbose_name_plural = 'media_stores'

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.file_name)

    def get_image_full(self):
        w, h = (self.img_width, self.img_height)
        url = MediaStore.make_iiif_image_server_url({
            "identifier": self.get_iiif_identifier(encode=True),
            "region": "full",
            "size": "full",
            "rotation": 0,
            "quality": "default",
            "format": self.file_extension,
        })
        full = {"width": w, "height": h, "url": url}
        return full

    def get_image_thumb(self):
        w, h = self.calc_thumb_size()
        url = MediaStore.make_iiif_image_server_url({
            "identifier": self.get_iiif_identifier(encode=True),
            "region": "full",
            "size": "{thumb_w},{thumb_h}".format(thumb_w=w, thumb_h=h),
            "rotation": 0,
            "quality": "default",
            "format": self.file_extension,
        })
        thumb = {"width": w, "height": h, "url": url}
        return thumb

    def calc_thumb_size(self):
        w, h = (self.img_width, self.img_height)
        if h > 200:
            thumb_h = 200
            thumb_w = int((float(w) / h) * thumb_h)
        else:
            thumb_h = h
            thumb_w = w
        return thumb_w, thumb_h
    
    def get_iiif_identifier(self, encode=False):
        identifier = "{bucket}/{keyname}".format(bucket=AWS_S3_BUCKET, keyname=self.get_s3_keyname())
        if encode:
            identifier = urllib.quote(identifier, safe='') # Make sure "/" is percent-encoded too!        
        return identifier

    def get_s3_keyname(self):
        return "{prefix}/images/{pk}/{file_name}".format(prefix=AWS_S3_KEY_PREFIX, pk=self.pk, file_name=self.file_name)

    def get_s3_url(self):
        '''Returns an absolute URL to the given item in the S3 bucket.'''
        return "http://s3.amazonaws.com/%s/%s" % (AWS_S3_BUCKET, self.get_s3_keyname())

    @classmethod
    def make_iiif_image_server_url(cls, iiif_spec):
        required_spec = ('identifier', 'region', 'size', 'rotation', 'quality', 'format')
        for k in iiif_spec.keys():
            if k not in required_spec:
                raise Exception("Error making IIIF image server URL. Missing '%s'. Given spec: %s" % (k, iiif_spec))
        url_format_str = '{base_url}{identifier}/{region}/{size}/{rotation}/{quality}.{format}'
        return url_format_str.format(base_url=IIIF_IMAGE_SERVER_URL, **iiif_spec)

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
    lti_context_id = models.CharField(max_length=128, null=True)
    lti_tool_consumer_instance_guid = models.CharField(max_length=1024, null=True)
    lti_tool_consumer_instance_name = models.CharField(max_length=128, null=True)
    lti_custom_canvas_api_domain = models.CharField(max_length=128, null=True)
    lti_context_title = models.CharField(max_length=256, null=True)
    lti_context_label = models.CharField(max_length=256, null=True)

    class Meta:
        verbose_name = 'course'
        verbose_name_plural = 'courses'
        ordering = ["title"]
        unique_together = ("lti_context_id", "lti_tool_consumer_instance_guid")

    def __unicode__(self):
        return "{0}:{1}:{2}".format(self.id, self.lti_context_id, self.title)

class CourseImage(BaseModel, SortOrderModelMixin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    owner = models.ForeignKey(UserProfile, null=True)
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
    
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'course_image'
        verbose_name_plural = 'course_images'

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})
        if self.media_store:
            self.media_store.reference_count += 1
            self.media_store.save() 
        super(CourseImage, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.media_store:
            self.media_store.reference_count -= 1
            self.media_store.save() 
        super(CourseImage, self).delete(*args, **kwargs)

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.title)
    

    @classmethod
    def get_course_images(cls, course_pk):
        images = cls.objects.filter(course__pk=course_pk).order_by('sort_order')
        return images
    
class Collection(BaseModel, SortOrderModelMixin):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
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
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    course_image = models.ForeignKey(CourseImage, on_delete=models.CASCADE)
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
