import os
import hashlib
import tempfile
from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.db import transaction
from media_service.models import MediaStore
from boto.s3.connection import S3Connection
from boto.s3.key import Key

# Required AWS settings
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACCESS_SECRET_KEY = settings.AWS_ACCESS_SECRET_KEY
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_S3_KEY_PREFIX = settings.AWS_S3_KEY_PREFIX

# Constants
S3_IMAGES_KEY_FORMAT = "{key_prefix}/{identifier}"

def get_s3_url(item_key):
    return "//s3.amazonaws.com/%s/%s" % (AWS_S3_BUCKET, item_key)

class MediaStoreUpload:
    def __init__(self, *args, **kwargs):
        self.file = kwargs.get('file', None)
        self.key_prefix = AWS_S3_KEY_PREFIX
        self.key_format_str = S3_IMAGES_KEY_FORMAT
        self.connection = S3Connection(AWS_ACCESS_KEY_ID, AWS_ACCESS_SECRET_KEY)
        self.bucket = self.connection.get_bucket(AWS_S3_BUCKET)

        self.instance = None
        self._file_md5hash = None

    @transaction.atomic
    def save(self):
        if self.instanceExists():
            self.instance = self.getInstance()
        else:
            self.instance = self.createInstance()
            self.instance.save()
            self.saveToBucket()
        return self.instance

    def is_valid(self):
        return True

    def saveToBucket(self):
        k = Key(self.bucket)
        k.key = self.getS3FileKey()
        self.file.seek(0)
        k.set_contents_from_file(self.file)
        return True

    def instanceExists(self):
        return MediaStore.objects.filter(file_md5hash=self.getFileHash()).exists()

    def getInstance(self):
        return MediaStore.objects.get(file_md5hash=self.getFileHash())

    def createInstance(self):
        attrs = {}
        attrs.update(self.getBaseTypeAttrs())
        attrs.update(self.getImageTypeAttrs())
        return MediaStore(**attrs)

    def getBaseTypeAttrs(self):
        attrs = {
            "file_name": self.createFileName(),
            "file_size": self.getFileSize(),
            "file_md5hash": self.getFileHash(),
            "file_type": self.getFileType(),
            "file_extension": self.getFileExtension(),
        }
        return attrs

    def getImageTypeAttrs(self):
        width, height = self.getImageDimensions()
        attrs = {
            'img_width': width,
            'img_height': height,
        }
        return attrs

    def getFileSize(self):
        return self.file.size

    def getFileType(self):
        return self.file.content_type

    def getFileExtension(self):
        name_parts = os.path.splitext(self.file.name)
        file_extension = ''
        if len(name_parts) > 1:
            file_extension = name_parts[1]
            if file_extension[0] == '.':
                file_extension = file_extension[1:]
        return file_extension.lower()
    
    def getImageDimensions(self):
        image_dimensions = get_image_dimensions(self.file)
        width = image_dimensions[0]
        height = image_dimensions[1]
        return width, height

    def getFileHash(self):
        if self._file_md5hash:
            return self._file_md5hash

        m = hashlib.md5()
        if self.file.multiple_chunks:
            for chunk in self.file.chunks():
                m.update(chunk)
        else:
            m.update(self.file.read())

        self._file_md5hash = m.hexdigest()

        return self._file_md5hash

    def getFileName():
        return self.file.name

    def getS3FileKey(self):
        if not self.instance:
            raise Exception("MediaStore instance required to construct S3 key")
        identifier = self.instance.get_iiif_identifier()
        key_prefix = self.key_prefix
        return self.key_format_str.format(key_prefix=key_prefix, identifier=identifier)

    def createFileName(self):
        return "%s.%s" % (self.getFileHash(), self.getFileExtension())

    def getNamedTempFile(self):
         return tempfile.NamedTemporaryFile('r+', -1)

    def writeFileTo(self, file_name):
        file = self.file
        with open(file_name, 'wb+') as dest:
            if file.multiple_chunks:
                for c in file.chunks():
                    dest.write(c)
            else:
                dest.write(file.read())
    
    def writeFileToNamedTempFile(self):
        tempfile = self.getNamedTempFile()
        self.writeFileTo(tempfile)
        return tempfile

