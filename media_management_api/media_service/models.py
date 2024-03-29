import json
import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import User
from django.db import Error, models, transaction
from django.db.models import Max

logger = logging.getLogger(__name__)

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
        """
        Returns the next available sort order for the given set of filters.
        """
        if filters is None:
            objects = self.objects.all()
        else:
            objects = self.objects.filter(**filters)
        result = objects.aggregate(n=Max("sort_order"))
        if result["n"] is None:
            return 1
        return result["n"] + 1


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
        verbose_name = "media_store"
        verbose_name_plural = "media_store"

    def __repr__(self):
        return "MediaStore:{0}:{1}".format(self.id, self.file_name)

    def __unicode__(self):
        return self.file_name

    def _get_iiif_identifier(self, encode=False):
        identifier = "{bucket}/{keyname}".format(
            bucket=AWS_S3_BUCKET, keyname=self.get_s3_keyname()
        )
        if encode:
            identifier = quote(
                identifier, safe=""
            )  # Make sure "/" is percent-encoded too!
        return identifier

    def get_iiif_base_url(self):
        identifier = self._get_iiif_identifier(encode=True)
        return "{base_url}{identifier}".format(
            base_url=IIIF_IMAGE_SERVER_URL, identifier=identifier
        )

    def get_iiif_full_url(self, thumb=False):
        w, h = (self.img_width, self.img_height)
        size = "full"
        if thumb:
            w, h = self.calc_thumb_size()
            size = "{thumb_w},{thumb_h}".format(thumb_w=w, thumb_h=h)

        url = MediaStore.make_iiif_image_server_url(
            {
                "identifier": self._get_iiif_identifier(encode=True),
                "region": "full",
                "size": size,
                "rotation": 0,
                "quality": "default",
                "format": "jpg",
            }
        )
        return {"width": w, "height": h, "url": url}

    def calc_thumb_size(self, max_height=200):
        w, h = (self.img_width, self.img_height)
        if h > max_height:
            thumb_h = max_height
            thumb_w = int((float(w) / h) * thumb_h)
        else:
            thumb_h = h
            thumb_w = w
        return thumb_w, thumb_h

    def get_s3_keyname(self):
        return "{prefix}/images/{pk}/{file_name}".format(
            prefix=AWS_S3_KEY_PREFIX, pk=self.pk, file_name=self.file_name
        )

    def get_s3_url(self):
        """Returns an absolute URL to the given item in the S3 bucket."""
        return "http://s3.amazonaws.com/%s/%s" % (AWS_S3_BUCKET, self.get_s3_keyname())

    @classmethod
    def make_iiif_image_server_url(cls, iiif_spec):
        required_spec = (
            "identifier",
            "region",
            "size",
            "rotation",
            "quality",
            "format",
        )
        for k in iiif_spec.keys():
            if k not in required_spec:
                raise Exception(
                    "Error making IIIF image server URL. Missing '%s'. Given spec: %s"
                    % (k, iiif_spec)
                )
        url_format_str = (
            "{base_url}{identifier}/{region}/{size}/{rotation}/{quality}.{format}"
        )
        return url_format_str.format(base_url=IIIF_IMAGE_SERVER_URL, **iiif_spec)


class UserProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="profile",
        null=True,
        blank=True,
    )
    sis_user_id = models.CharField(max_length=60, unique=True, blank=True, null=True)

    @classmethod
    def get_or_create_profile(cls, sis_user_id=None):
        user_profiles = cls.objects.filter(sis_user_id=sis_user_id)
        user_profile = None
        if len(user_profiles) == 0:
            user_profile = cls(sis_user_id=sis_user_id)
            user_profile.save()
        else:
            user_profile = user_profiles[0]
        if not user_profile.user:
            user = User.objects.create_user(
                username="UserProfile:%s" % user_profile.id, password=None
            )
            user_profile.user = user
            user_profile.save()
        return user_profile

    class Meta:
        verbose_name = "user_profile"
        verbose_name_plural = "user_profiles"

    def __repr__(self):
        return "UserProfile:%s:%s" % (self.pk, self.sis_user_id)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "%s:%s" % (self.pk, self.sis_user_id)


class Course(BaseModel):
    title = models.CharField(max_length=255)
    sis_course_id = models.CharField(max_length=128, null=True, unique=True)
    canvas_course_id = models.IntegerField(null=True)
    lti_context_id = models.CharField(max_length=128, null=True)
    lti_tool_consumer_instance_guid = models.CharField(max_length=1024, null=True)
    lti_tool_consumer_instance_name = models.CharField(max_length=128, null=True)
    lti_context_title = models.CharField(max_length=256, null=True)
    lti_context_label = models.CharField(max_length=256, null=True)

    class Meta:
        verbose_name = "course"
        verbose_name_plural = "courses"
        ordering = ["title"]
        unique_together = ["lti_context_id", "lti_tool_consumer_instance_guid"]

    def copy(self, dest_course):
        """
        Copies all of the collections and resources from this course to a destination course.

        :param dest_course: destination course
        :return: a CourseCopy instance
        """
        copy_data = {
            "total": 0,
            "resources": {},
            "collections": {},
            "collection_resources": {},
        }
        course_copy = CourseCopy(source=self, dest=dest_course)
        course_copy.initiate()

        logger.info(
            "Copy %d started from course %s to %s"
            % (course_copy.pk, self.pk, dest_course.pk)
        )
        try:
            with transaction.atomic():
                # Copy collections from the course
                for collection in self.collections.all():
                    logger.info(
                        "Copying collection %s [course_copy_id=%s]"
                        % (collection.pk, course_copy.pk)
                    )
                    from_pk, to_pk = collection.copy_to(dest_course)
                    copy_data["collections"][from_pk] = to_pk
                    copy_data["total"] += 1

                # Copy resources from the course
                for resource in self.resources.all():
                    logger.info(
                        "Copying resource %s [course_copy_id=%s]"
                        % (resource.pk, course_copy.pk)
                    )
                    from_pk, to_pk = resource.copy_to(dest_course)
                    copy_data["resources"][from_pk] = to_pk
                    copy_data["total"] += 1

                # Copy mapping of the resources and collections from the course
                for collection in self.collections.all():
                    for collection_resource in collection.resources.all():
                        logger.info(
                            "Copying collection resource %s [course_copy_id=%s]"
                            % (collection_resource.pk, course_copy.pk)
                        )
                        dest_collection_pk = copy_data["collections"][
                            collection_resource.collection_id
                        ]
                        dest_resource_pk = copy_data["resources"][
                            collection_resource.resource_id
                        ]
                        from_pk, to_pk = collection_resource.copy_to(
                            dest_collection_pk, dest_resource_pk
                        )
                        copy_data["collection_resources"][from_pk] = to_pk
                        copy_data["total"] += 1
        except Error as e:
            logger.exception(
                "Copy error from course %s to %s"
                % (course_copy.source.pk, course_copy.dest.pk)
            )
            course_copy.fail(str(e))
            raise e

        course_copy.complete(copy_data)
        logger.info(
            "Copy %d completed from course %s to %s"
            % (course_copy.pk, course_copy.source.pk, course_copy.dest.pk)
        )

        return course_copy

    def __repr__(self):
        return "Course:%s:%s" % (self.pk, self.title)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.title


class CourseUser(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)

    @classmethod
    def get_course_ids(cls, user_profile):
        return list(
            cls.objects.filter(user_profile=user_profile)
            .values_list("course_id", flat=True)
            .order_by("id")
        )

    @classmethod
    def add_user_to_course(cls, user=None, course_id=None, is_admin=False):
        return cls.add_to_course(
            user_profile=user.profile, course_id=course_id, is_admin=is_admin
        )

    @classmethod
    def add_to_course(cls, user_profile=None, course_id=None, is_admin=False):
        # Will raise Course.DoesNotExist if invalid course_id
        Course.objects.get(pk=course_id)

        try:
            course_user = cls.objects.get(
                user_profile=user_profile, course_id=course_id
            )
        except CourseUser.DoesNotExist:
            course_user = cls(user_profile=user_profile, course_id=course_id)
        except CourseUser.MultipleObjectsReturned:
            cls.objects.filter(user_profile=user_profile, course_id=course_id).delete()
            course_user = cls(user_profile=user_profile, course_id=course_id)

        course_user.is_admin = is_admin
        course_user.save()
        return course_user

    class Meta:
        verbose_name = "course user"
        verbose_name_plural = "course users"
        unique_together = ["course", "user_profile", "is_admin"]

    def __repr__(self):
        return "CourseUser:%s" % (self.pk)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return str(self.pk)


def metadata_default():
    return json.dumps([])


class Resource(BaseModel, SortOrderModelMixin):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="resources"
    )
    owner = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="resources",
        null=True,
        blank=True,
    )
    media_store = models.ForeignKey(MediaStore, null=True, on_delete=models.SET_NULL)
    is_upload = models.BooleanField(default=True, null=False)
    original_file_name = models.CharField(max_length=4096, null=True)
    img_type = models.CharField(max_length=128, null=True, blank=True)
    img_url = models.CharField(max_length=4096, null=True, blank=True)
    img_width = models.PositiveIntegerField(null=True, blank=True)
    img_height = models.PositiveIntegerField(null=True, blank=True)
    thumb_url = models.CharField(max_length=4096, null=True, blank=True)
    thumb_width = models.PositiveIntegerField(null=True, blank=True)
    thumb_height = models.PositiveIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    metadata = models.TextField(blank=True, default=metadata_default)
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "resource"
        verbose_name_plural = "resources"
        ordering = ["course", "sort_order", "title"]

    def save(self, *args, **kwargs):
        if self.course and not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})

        # This code is to ensure we only ever have a JSON "list" saved in the metadata field.
        # Note that rigorous validation of the data structure happens in the serializer. A better
        # solution would be to implement a true "JSONField" with rigorous validation on the model.
        try:
            self.metadata = (
                self.metadata
                if isinstance(json.loads(self.metadata), list)
                else metadata_default()
            )
        except (TypeError, ValueError):
            self.metadata = metadata_default()

        if self.media_store:
            self.media_store.reference_count += 1
            self.media_store.save()

        super(Resource, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.media_store:
            self.media_store.reference_count -= 1
            self.media_store.save()
        super(Resource, self).delete(*args, **kwargs)

    def copy_to(self, course_pk):
        from_pk = self.pk
        self.pk = None
        self.course = course_pk
        self.sort_order = None
        self.save(force_insert=True)
        to_pk = self.pk
        assert from_pk != to_pk, "copy should create a new resource instance"
        return from_pk, to_pk

    def get_representation(self):
        if self.media_store is None:
            image_type = self.img_type
            image_url = self.img_url
            image_width = self.img_width
            image_height = self.img_height
            thumb_url = self.thumb_url
            thumb_width = self.thumb_width
            thumb_height = self.thumb_height
            iiif_base_url = None
        else:
            thumb = self.media_store.get_iiif_full_url(thumb=True)
            full = self.media_store.get_iiif_full_url(thumb=False)
            iiif_base_url = self.media_store.get_iiif_base_url()
            image_type = self.media_store.file_type
            image_url = full["url"]
            image_width = full["width"]
            image_height = full["height"]
            thumb_url = thumb["url"]
            thumb_width = thumb["width"]
            thumb_height = thumb["height"]
        data = {
            "image_type": image_type,
            "image_width": image_width,
            "image_height": image_height,
            "image_url": image_url,
            "thumb_width": thumb_width,
            "thumb_height": thumb_height,
            "thumb_url": thumb_url,
            "iiif_base_url": iiif_base_url,
        }
        return data

    def load_metadata(self):
        if self.metadata:
            return json.loads(self.metadata)
        else:
            return []

    def __repr__(self):
        return "Resource:{0}:{1}".format(self.id, self.title)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.title

    @classmethod
    def get_course_images(cls, course_pk):
        images = cls.objects.filter(course__pk=course_pk).order_by("sort_order")
        return images


class Collection(BaseModel, SortOrderModelMixin):
    IIIF_SOURCE_IMAGES = "images"
    IIIF_SOURCE_CUSTOM = "custom"
    IIIF_SOURCE_CHOICES = (
        (IIIF_SOURCE_IMAGES, "Collection Images"),
        (IIIF_SOURCE_CUSTOM, "IIIF Manifest"),
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="collections"
    )
    sort_order = models.IntegerField(default=0)
    iiif_source = models.CharField(
        max_length=100, choices=IIIF_SOURCE_CHOICES, default=IIIF_SOURCE_IMAGES
    )
    iiif_custom_manifest_url = models.CharField(max_length=4096, null=False, blank=True)
    iiif_custom_canvas_id = models.CharField(max_length=4096, null=False, blank=True)

    class Meta:
        verbose_name = "collection"
        verbose_name_plural = "collections"
        ordering = ["course", "sort_order", "title"]

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order({"course__pk": self.course.pk})
        super(Collection, self).save(*args, **kwargs)

    def copy_to(self, course_pk):
        from_pk = self.pk
        self.pk = None
        self.course = course_pk
        self.sort_order = None
        self.save(force_insert=True)
        to_pk = self.pk
        assert from_pk != to_pk, "copy should create a new collection instance"
        return from_pk, to_pk

    def __repr__(self):
        return "Collection:%s:%s" % (self.id, self.title)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.title

    @classmethod
    def get_course_collections(cls, course_pk):
        collections = cls.objects.filter(course__pk=course_pk).order_by("sort_order")
        return collections


class CollectionResource(BaseModel, SortOrderModelMixin):
    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="resources"
    )
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="collection_resources"
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "collection resource"
        verbose_name_plural = "collection resources"
        ordering = ["collection", "sort_order", "resource"]

    def save(self, *args, **kwargs):
        if not self.sort_order:
            self.sort_order = self.next_sort_order(
                {"collection__pk": self.collection.pk}
            )
        super(CollectionResource, self).save(*args, **kwargs)

    def copy_to(self, collection_pk, resource_pk):
        from_pk = self.pk
        self.pk = None
        self.collection_id = collection_pk
        self.resource_id = resource_pk
        self.sort_order = None
        self.save(force_insert=True)
        to_pk = self.pk
        assert from_pk != to_pk, "copy should create a new collection resource instance"
        return from_pk, to_pk

    def __repr__(self):
        return "CollectionResource:{0}".format(self.pk)

    def __unicode__(self):
        return str(self.pk)

    @classmethod
    def get_collection_images(cls, collection_pk):
        images = cls.objects.filter(collection__pk=collection_pk).order_by("sort_order")
        return images


class CourseCopy(BaseModel):
    STATE_INITIATED = "initiated"
    STATE_COMPLETED = "completed"
    STATE_ERROR = "error"
    STATE_CHOICES = (
        (STATE_INITIATED, "Initiated"),
        (STATE_COMPLETED, "Completed"),
        (STATE_ERROR, "Error"),
    )
    source = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="source_copies"
    )
    dest = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="dest_copies"
    )
    state = models.CharField(
        max_length=100, choices=STATE_CHOICES, default=STATE_INITIATED
    )
    error = models.TextField()
    data = models.TextField(blank=True, default="{}")

    class Meta:
        verbose_name = "course copy"
        verbose_name_plural = "course copy"
        ordering = ["-created"]

    def initiate(self, data=None):
        self.state = self.STATE_INITIATED
        if data is not None:
            self.data = json.dumps(data)
        self.save()
        return self

    def complete(self, data=None):
        self.state = self.STATE_COMPLETED
        if data is not None:
            self.data = json.dumps(data)
        self.save()
        return self

    def fail(self, error_msg):
        self.state = self.STATE_ERROR
        self.error = error_msg
        self.save()
        return self

    def updateData(self, data):
        self.data = json.dumps(data)
        self.save(update_fields=["data", "updated"])
        return self

    def loadData(self):
        if self.data:
            return json.loads(self.data)
        else:
            return {}

    def __repr__(self):
        return "CourseCopy:%s" % (self.pk)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return str(self.pk)
