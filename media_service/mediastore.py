import os
import hashlib
import tempfile
import magic
import logging
from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from media_service.models import MediaStore

# Required AWS settings
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACCESS_SECRET_KEY = settings.AWS_ACCESS_SECRET_KEY
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_S3_KEY_PREFIX = settings.AWS_S3_KEY_PREFIX

class MediaStoreUploadException(Exception):
    pass

class MediaStoreUpload:
    '''
    The MediaStoreUpload class is responsible for storing a django UploadedFile.

    This class is designed such that:
        1. One and only one file should exist in the store at a given time (no duplicates).
        2. Files are stored in one S3 bucket.

    Given an uploaded file, this class will check to see if an identical file already
    exists in the store according to its signature (i.e. MD5 checksum). If the file is
    already in the store, it will return that MediaStore instance. Otherwise, it will
    create a new MediaStore instance with metadata about the file (i.e. height, width, type, etc),
    and then store the contents of the file in the designated S3 bucket.

    Public methods:
        - save()
        - is_valid()
    
    Exceptions:
        - MediaStoreUploadException

    Example usage:
        media_store_upload = MediaStoreUpload(file=request.FILES['upload'])
        if media_store_upload.is_valid():
            media_store_instance = media_store_upload.save()
    '''
    def __init__(self, uploaded_file):
        if not isinstance(uploaded_file, UploadedFile):
            raise MediaStoreUploadException("File must be an instance of django.core.files.UploadedFile")

        self.file = uploaded_file 
        self.instance = None # Holds MediaStore instance
        self._file_md5hash = None # holds cached MD5 hash of the file

    @transaction.atomic
    def save(self):
        '''
        Returns a MediaStore instance. If the file already exists, returns the existing
        MediaStore instance, otherwise saves a new MediaStore instance and saves the
        file to the S3 bucket.
        '''
        if self.instanceExists():
            self.instance = self.getInstance()
        else:
            self.instance = self.createInstance()
            self.instance.save()
            self.saveToBucket()
        return self.instance

    def is_valid(self):
        '''
        Returns true if the uploaded file is valid, false otherwise.
        '''
        return True

    def get_s3_connection(self):
        '''
        Returns an S3Connection instance.
        '''
        return S3Connection(AWS_ACCESS_KEY_ID, AWS_ACCESS_SECRET_KEY)

    def get_s3_bucket(self, connection):
        '''
        Returns the bucket where files are stored.
        '''
        return connection.get_bucket(AWS_S3_BUCKET)


    def saveToBucket(self):
        '''
        Saves the django UploadedFile to the designated S3 bucket.
        '''
        connection = self.get_s3_connection()
        bucket = self.get_s3_bucket(connection)

        k = Key(bucket)
        k.key = self.getS3FileKey()
        self.file.seek(0)
        k.set_contents_from_file(self.file, replace=True)

        return True

    def instanceExists(self):
        '''
        Returns true if a MediaStore instance already exists for the file, otherwise false.
        '''
        return MediaStore.objects.filter(file_md5hash=self.getFileHash()).exists()

    def getInstance(self):
        '''
        Returns the MediaStore instance with the same file signature (MD5 checksum) that was uploaded.
        '''
        return MediaStore.objects.get(file_md5hash=self.getFileHash())

    def createInstance(self):
        '''
        Returns a new instance of MediaStore for the uploaded file.
        The caller must save() the instance.
        '''
        attrs = {}
        attrs.update(self.getBaseTypeAttrs())
        attrs.update(self.getImageTypeAttrs())
        return MediaStore(**attrs)

    def getBaseTypeAttrs(self):
        '''
        Returns the base attributes of the file (not type-specific).
        '''
        attrs = {
            "file_name": self.createFileName(),
            "file_size": self.getFileSize(),
            "file_md5hash": self.getFileHash(),
            "file_type": self.getFileType(),
            "file_extension": self.getFileExtension(),
        }
        return attrs

    def getImageTypeAttrs(self):
        '''
        Returns the image-specific attributes of the file.
        '''
        width, height = self.getImageDimensions()
        attrs = {
            'img_width': width,
            'img_height': height,
        }
        return attrs

    def getFileSize(self):
        '''
        Returns the uploaded file's size, in bytes.
        '''
        return self.file.size

    def getFileType(self):
        '''
        Returns the MIME type of the uploaded file via python-magic (libmagic).
        
        NOTE: there are *two* python libraries named "magic" so if this method is generating
        errors, it's possible that the other "magic" is installed on the system.
        '''
        buf = self.file.chunks(1024).next()
        file_type = magic.from_buffer(buf, mime=True)
        return file_type

    def getFileExtension(self):
        '''
        Returns the lowercase file extension (no dot). Example: "jpg" or "gif"
        '''
        name_parts = os.path.splitext(self.file.name)
        file_extension = ''
        if len(name_parts) > 1:
            file_extension = name_parts[1]
            if file_extension[0] == '.':
                file_extension = file_extension[1:]
        return file_extension.lower()
    
    def getImageDimensions(self):
        '''
        Returns the dimensions of the uploaded image file.
        
        Borrows Django's django.core.files.images.get_image_dimensions
        method to get the dimensions via Pillow (python imaging module).
        '''
        image_dimensions = get_image_dimensions(self.file)
        width = image_dimensions[0]
        height = image_dimensions[1]
        return width, height

    def getFileHash(self):
        '''
        Returns an MD5 hash of the file contents to use as a file signature.
        '''
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

    def getS3FileKey(self):
        '''
        Returns the "key" name that will be used to store the file object in the S3 bucket.
        '''
        if not self.instance:
            raise MediaStoreUploadException("MediaStore instance required to construct S3 key")
        return self.instance.get_s3_keyname()

    def createFileName(self):
        '''
        Returns a file name from the combination of the file signature (hash) and the file extension.
        '''
        return "%s.%s" % (self.getFileHash(), self.getFileExtension())

    def getNamedTempFile(self):
        '''
        Utility function to get a named temporary file.
        '''
        return tempfile.NamedTemporaryFile('r+', -1)

    def writeFileTo(self, file_name):
        '''
        Utility function to write the uploaded file contents to a given file name.
        '''
        file = self.file
        with open(file_name, 'wb+') as dest:
            if file.multiple_chunks:
                for c in file.chunks():
                    dest.write(c)
            else:
                dest.write(file.read())

