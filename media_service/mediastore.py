import os
import hashlib
import mimetypes
import tempfile

from django.conf import settings
from media_service.models import MediaStore
from boto.s3.connection import S3Connection
from boto.s3.key import Key

# Required AWS settings
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACCESS_SECRET_KEY = settings.AWS_ACCESS_SECRET_KEY
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_S3_KEY_PREFIX = settings.AWS_S3_KEY_PREFIX

def get_s3_url(item_key):
    return "//s3.amazonaws.com/%s/%s" % (AWS_S3_BUCKET, item_key)

class MediaStoreService:
    def __init__(self, *args, **kwargs):
        self._file_md5hash = None
    
    def recordExists(self):
        return MediaStore.objects.filter(file_md5hash=self.getFileHash()).exists()

    def lookupRecord(self):
        return MediaStore.objects.filter(file_md5hash=self.getFileHash())[0]

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
    
class MediaStoreS3:
    def __init__(self, *args, **kwargs):
        self.connection = MediaStoreS3.connect()
        self.bucket = MediaStoreS3.getBucket(self.connection)
    
    @staticmethod
    def connect():
        return S3Connection(AWS_ACCESS_KEY_ID, AWS_ACCESS_SECRET_KEY)
    
    @staticmethod
    def getBucket(connection):
        return connection.get_bucket(AWS_S3_BUCKET)
