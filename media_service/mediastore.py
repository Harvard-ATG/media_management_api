import io
import os
import hashlib
import tempfile
import magic
import logging
import zipfile
import re
from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import UploadedFile
from django.core.files.base import File
from django.db import transaction
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from PIL import Image

from media_service.models import MediaStore

# Required AWS settings
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACCESS_SECRET_KEY = settings.AWS_ACCESS_SECRET_KEY
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_S3_KEY_PREFIX = settings.AWS_S3_KEY_PREFIX

logger = logging.getLogger(__name__)

class MediaStoreUploadException(Exception):
    pass

def processFileUploads(filelist):
    '''
    processes a file upload list, unzipping all zips
    returns a new list with unzipped files
    '''
    newlist = []
    for file in filelist:
        if zipfile.is_zipfile(file):
            # unzip and append to the list
            zip = zipfile.ZipFile(file, "r")
            for f in zip.namelist():
                logger.debug("ZipFile content: %s" % f)
                zf = zip.open(f).read()
                newfile = File(io.BytesIO(zf))
                newfile.name = f

                # avoiding temp files added to archive
                if "__MACOSX" not in newfile.name and not re.match(r".*\/$", newfile.name):
                    newlist.append(newfile)
        else:
            newlist.append(file)

    return newlist

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
    VALID_IMAGE_EXTENSIONS = ('jpg', 'gif', 'png')

    def __init__(self, uploaded_file):

        if not isinstance(uploaded_file, UploadedFile) and not isinstance(uploaded_file, File):
            raise MediaStoreUploadException("File must be an instance of django.core.files.UploadedFile or django.core.files.base.File")

        self.file = uploaded_file
        self.instance = None # Holds MediaStore instance
        self._file_md5hash = None # holds cached MD5 hash of the file
        self._is_valid = True
        self._error = {}

    @transaction.atomic
    def save(self):
        '''
        Returns a MediaStore instance. If the file already exists, returns the existing
        MediaStore instance, otherwise saves a new MediaStore instance and saves the
        file to the S3 bucket.
        '''
        if self.instanceExists():
            logger.debug("instance exists")
            self.instance = self.getInstance()

        else:
            logger.debug("creating new instance")
            self.instance = self.createInstance()
            self.instance.save()
            self.saveToBucket()
        return self.instance

    def isValid(self):
        '''
        Returns true if the uploaded file is valid, false otherwise.
        '''
        self.validateImageExtension()
        self.validateImageOpens()

        logger.debug("isValid: %s errors: %s" % (self._is_valid, self.getErrors()))
        return self._is_valid

    def error(self, name, error):
        '''
        Saves a validation error.
        '''
        self._is_valid = False
        self._error[name] = error

    def getErrors(self):
        return "".join([self._error[k] for k in sorted(self._error)])

    def validateImageExtension(self):
        '''
        Validates that the image extension is valid.
        '''
        ext = self.getFileExtension()
        valid_exts = self.VALID_IMAGE_EXTENSIONS
        if ext not in valid_exts:
            self.error('extension', "Image extension '%s' is invalid [must be one of %s]. " % (ext, valid_exts))
            return False
        return True

    def validateImageOpens(self):
        '''
        Validates that the given image can be opened and identified by the Pillow image library.
        '''
        try:
            Image.open(self.file)
        except Exception as e:
            self.error('open', "Image cannot be opened or identified [%s]. " % str(e))
            return False
        return True

    def getS3connection(self):
        '''
        Returns an S3Connection instance.
        '''
        return S3Connection(AWS_ACCESS_KEY_ID, AWS_ACCESS_SECRET_KEY)

    def getS3bucket(self, connection):
        '''
        Returns the bucket where files are stored.
        '''
        return connection.get_bucket(AWS_S3_BUCKET)

    def saveToBucket(self):
        '''
        Saves the django UploadedFile to the designated S3 bucket.
        '''
        connection = self.getS3connection()
        bucket = self.getS3bucket(connection)

        k = Key(bucket)
        k.key = self.getS3FileKey()
        self.file.seek(0)

        logger.debug("Saving file to S3 bucket with key=%s" % k.key)
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
        logger.debug("Creating instance with attrs=%s" % attrs)
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
        logger.debug("getFileExtension: %s" % self.file.name)
        file_extension = ''
        if len(name_parts) > 1:
            file_extension = name_parts[1]
            if file_extension[0] == '.':
                file_extension = file_extension[1:]
        file_extension = file_extension.lower()

        # Set canonical file extension, if applicable (i.e ."jpeg" -> "jpg")
        canonical_map = {"jpeg": "jpg"}
        if file_extension in canonical_map:
            file_extension = canonical_map[file_extension]

        return file_extension

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
