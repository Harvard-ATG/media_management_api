import io
import os
import hashlib
import tempfile
import magic
import logging
import zipfile
import re
import requests
import tempfile
import urlparse
import contextlib
from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import UploadedFile
from django.core.files.base import File
from django.db import transaction
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from PIL import Image

from media_service.models import MediaStore

logger = logging.getLogger(__name__)

# Required AWS settings
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACCESS_SECRET_KEY = settings.AWS_ACCESS_SECRET_KEY
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_S3_KEY_PREFIX = settings.AWS_S3_KEY_PREFIX

# Configurable settings for media store
VALID_IMAGE_EXTENSIONS = ('jpg', 'gif', 'png', 'tif', 'tiff')
VALID_IMAGE_EXT_FOR_TYPE = {
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'image/png': 'png',
    'image/tiff': 'tif',
}
VALID_IMAGE_TYPES = sorted(VALID_IMAGE_EXT_FOR_TYPE.keys())

class MediaStoreException(Exception):
    pass

def guessImageExtensionFromUrl(url):
    '''
    Attempts to extract an image extension (jpg, png, etc) from the URL to the image.
    Returns None when no extension can be identified.
    '''
    extension = None
    o = urlparse.urlparse(url)
    if '/' in o.path and len(o.path) > 1:
        name = o.path.split('/')[-1]
        if '.' in name:
            extension = name.rsplit('.')[-1].lower()
    return extension

def fetchRemoteImage(url):
    '''
    Returns a temporary file object.
    Raises a requests.exceptions.HTTPError if there's a 4xx or 5xx response.
    Raises a MediaStoreException if the response content type header doesn't contain "image".
    '''
    extension = guessImageExtensionFromUrl(url)
    suffix = '' if extension is None else '.' + extension
    max_size = 10 * pow(2, 20) # 10 megabytes
    request_headers = {
        # Spoofing the user agent to work around image providers that reject requests from "robots" (403 forbidden response)
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',

        # Make explicit the image types we are willing to accept
        'Accept': "{image_types},image/*;q=0.8".format(image_types=', '.join(VALID_IMAGE_TYPES)),
    }

    # Use HTTP for all requests because of SSL errors
    url = "http://" + url[8:] if url.startswith("https://") else url

    with contextlib.closing(requests.get(url, headers=request_headers, stream=True, verify=False)) as res:
        logger.debug("Fetched remote image. Request url=%s headers=%s Response code=%s headers=%s" % (url, request_headers, res.status_code, res.headers))
        res.raise_for_status()

        # Check the size before attempting to download the response content
        if 'content-length' in res.headers:
            if int(res.headers['content-length']) > max_size:
                raise MediaStoreException("Image is too large (%s > %s bytes)." % (res.headers['content-length'], max_size))
            elif int(res.headers['content-length']) == 0:
                raise MediaStoreException("Image is empty (0 bytes).")
    
        # Check to see that we got some kind of image in the response,
        # with the intent that the image will be checked more thorougly by another method
        if 'image' not in res.headers.get('content-type', ''):
            raise MediaStoreException("Invalid content type: %s. Expected an image type." % res.headers['content-type'])

        # Save the image content to a temporary file
        f = tempfile.TemporaryFile(suffix=suffix)
        for chunk in res.iter_content(chunk_size=1024*1024):
            f.write(chunk)
        return f

    return None

def processRemoteImages(items):
    '''
    process a list of remote images to import
    returns a dict that maps image urls to image files that have been fetched and cached locally.
    '''
    logger.debug("Processing remote images: %s" % items)
    processed = {}
    for index, item in enumerate(items):
        url = item.get('url', None)
        if url is None:
            raise MediaStoreException("Missing 'url' for item %d in list of items: %s" % (index, items))
        data = {
            "title": item.get("title", "Untitled") or "Untitled",
            "description": item.get("description", ""),
        }
        image_file = fetchRemoteImage(url)
        processed[url] = {
            "file": File(image_file),
            "data": data
        }
    return processed

def processFileUploads(filelist):
    '''
    processes a file upload list, unzipping all zips
    returns a dict that maps indexes to processed file objects
    '''
    newlist = []
    for file in filelist:
        if zipfile.is_zipfile(file):
            # unzip and append to the list
            zip = zipfile.ZipFile(file, "r")
            for f in zip.namelist():
                logger.debug("Extracting ZipFile: %s" % f)

                if f.endswith('/'):
                    logger.debug("Skipping directory entry: %s" % f)
                    continue
                if "__MACOSX" in f or ".DS_Store" in f:
                    logger.debug("Skipping MAC OS X resource file artifact: %s" % f)
                    continue

                zf = zip.open(f).read()
                newfile = File(io.BytesIO(zf))
                newfile.name = f
                newlist.append(newfile)
        else:
            newlist.append(file)

    processed = dict(enumerate(newlist))
    return processed


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
        - MediaStoreException

    Example usage:
        media_store_upload = MediaStoreUpload(file=request.FILES['upload'])
        if media_store_upload.is_valid():
            media_store_instance = media_store_upload.save()
    '''

    def __init__(self, uploaded_file):

        if not isinstance(uploaded_file, UploadedFile) and not isinstance(uploaded_file, File):
            raise MediaStoreException("File must be an instance of django.core.files.UploadedFile or django.core.files.base.File")

        self.file = uploaded_file
        self.instance = None # Holds MediaStore instance
        self._file_md5hash = None # holds cached MD5 hash of the file
        self._is_valid = True
        self._error = {}
        self._raise_for_error = False

    def raise_for_error(self):
        self._raise_for_error = True

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
        self.validate()
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

    def validate(self):
        self.validateImageType()
        self.validateImageOpens()
        self.validateImageExtension()
        return self

    def validateImageType(self):
        filetype = self.getFileType()
        if filetype not in VALID_IMAGE_TYPES:
            errmsg = "Image type '%s' is not supported. Please ensure the image is one of the supported image types." %  filetype
            self.error('type', errmsg)
            if self._raise_for_error:
                raise MediaStoreException(errmsg)
            return False
        return True

    def validateImageExtension(self):
        '''
        Validates that the image extension is valid.
        '''
        ext = self.getFileExtension()
        if ext not in VALID_IMAGE_EXTENSIONS:
            errmsg = "Image extension '%s' is not recognized." % ext
            self.error('extension', errmsg)
            if self._raise_for_error:
                raise MediaStoreException(errmsg)
            return False
        return True

    def validateImageOpens(self):
        '''
        Validates that the given image can be opened and identified by the Pillow image library.
        '''
        try:
            Image.open(self.file)
        except Exception as e:
            errmsg = "Image cannot be opened or identified."
            self.error('open', errmsg)
            if self._raise_for_error:
                raise MediaStoreException(errmsg)
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

        headers = {"Content-Type": self.instance.file_type}
        logger.debug("Saving file to S3 bucket with key=%s headers=%s" % (k.key, headers))
        k.set_contents_from_file(self.file, replace=True, headers=headers)

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
        file_type = self.getFileType()
        file_extension = ''

        # Attempt to get the file extension from its mime type
        if file_type in VALID_IMAGE_EXT_FOR_TYPE:
            file_extension = VALID_IMAGE_EXT_FOR_TYPE.get(file_type, '')

        # Otherwise fall back to the file name
        if not file_extension:
            name_parts = os.path.splitext(self.file.name)
            if len(name_parts) > 1:
                file_extension = name_parts[1]
                if len(file_extension) > 0 and file_extension[0] == '.':
                    file_extension = file_extension[1:]
            file_extension = file_extension.lower()

            # Set canonical file extension for JPEGs (i.e ."jpeg" -> "jpg")
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
            raise MediaStoreException("MediaStore instance required to construct S3 key")
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
