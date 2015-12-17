import os
import hashlib
import tempfile
from django.conf import settings
from django.core.files.images import get_image_dimensions
from media_service.models import MediaStore
from boto.s3.connection import S3Connection
from boto.s3.key import Key

# Required AWS settings
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACCESS_SECRET_KEY = settings.AWS_ACCESS_SECRET_KEY
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_S3_KEY_PREFIX = settings.AWS_S3_KEY_PREFIX

IMAGE_TYPE = 'image'

def get_s3_url(item_key):
    return "//s3.amazonaws.com/%s/%s" % (AWS_S3_BUCKET, item_key)

class MediaStoreUpload:
    def __init__(self, *args, **kwargs):
        self.file = kwargs.get('file', None)
        self._file_md5hash = None
        self.media_type = kwargs.get('media_type', IMAGE_TYPE)
        self.key_prefix = AWS_S3_KEY_PREFIX
        self.connection = S3Connection(AWS_ACCESS_KEY_ID, AWS_ACCESS_SECRET_KEY)
        self.bucket = self.connection.get_bucket(AWS_S3_BUCKET)
        self.instance = None

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
        k.key = self.getStoreFilePath()
        if self.file.multiple_chunks:
            # TODO: http://boto.cloudhackers.com/en/latest/s3_tut.html#storing-large-data
            pass
        file_content = self.file.read()
        k.set_contents_from_string(file_content)

    def instanceExists(self):
        return MediaStore.objects.filter(file_md5hash=self.getFileHash()).exists()

    def getInstance(self):
        return MediaStore.objects.filter(file_md5hash=self.getFileHash())[0]

    def createInstance(self):
        attrs = self.getBaseTypeAttrs()
        if self.media_type == IMAGE_TYPE:
            attrs.update(self.getImageTypeAttrs())
        return MediaStore(**attrs)

    def getBaseTypeAttrs(self):
        attrs = {
            "file_name": self.createFileName(),
            "file_size": self.getFileSize(),
            "file_md5hash": self.getFileHash(),
            "file_type": self.getFileType(),
        }
        return attrs

    def getImageTypeAttrs(self):
        width, height = self.getImageDimensions()
        attrs = {
            'img_width': width,
            'img_height': height,
        }
        return attrs

    def getImageType(self):
        return None

    def getFileSize(self):
        return self.file.size

    def getFileType(self):
        return self.file.content_type
    
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

    def getStoreFilePath(self):
        if not self.instance:
            raise Exception("MediaStore instance required")
        file_path = "{prefix}/{folder}/{name}".format(
            prefix=self.key_prefix,
            folder=self.instance.pk,
            name=self.instance.file_name
        )
        return file_path

    def createFileName(self):
        name_parts = os.path.splitext(self.file.name)
        file_extension = ''
        if len(name_parts) > 1:
            file_extension = name_parts[1]
        return self.getFileHash() + file_extension.lower()

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

