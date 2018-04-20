import unittest
import base64
import re
import zipfile
import tempfile
import mock
import requests
from mock import MagicMock, patch
from django.core.files.uploadedfile import SimpleUploadedFile
from .. import mediastore
from ..mediastore import MediaStoreUpload, MediaStoreException
from ..models import MediaStore

TEST_FILES = {
    'test.png': {
        'filename': 'test.png',
        'extension': 'png',
        'content-type': 'image/png',
        # image content from: http://dummyimage.com/24x24/000/fff&text=Test
        'content': base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAABgAAAAYBAMAAAASWSDLAAAAFVBMVEUAAAD///8fHx9fX19/f38/Pz+fn5+WwvWOAAAAPElEQVQYlWNgGHjAZGIMocEkswKYYoFxjA2UTdVMIRxmBSMjuAyLsRGzEZwD0gLjMLkaKBuzmsKMp4WbAVr9BJo70GnDAAAAAElFTkSuQmCC'),
        'dimensions': {'w': 24,'h': 24},
    },
    'test.badextension': {
        'filename': 'test.badextension',
        'extension': 'badextension',
        'content-type': None,
        'content': None
    },
    'empty.jpg': {
        'filename': 'test.jpg',
        'extension': 'jpg',
        'content-type': 'image/jpeg',
        'content': None
    },
    'empty.jpeg': {
        'filename': 'test.jpeg',
        'extension': 'jpg',
        'content-type': 'image/jpeg',
        'content': None
    },
}

class TestMediaStoreUpload(unittest.TestCase):

    test_files = TEST_FILES

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def createUploadedFile(self, test_file):
        return SimpleUploadedFile.from_dict({
            'filename': test_file['filename'],
            'content-type': test_file['content-type'],
            'content': test_file['content'],
        })

    def createMediaStoreUpload(self, test_file):
        uploaded_file = self.createUploadedFile(test_file)
        return MediaStoreUpload(uploaded_file)

    def testCreateMediaStoreUpload(self):
        instance = self.createMediaStoreUpload(self.test_files['test.png'])
        self.assertTrue(isinstance(instance, MediaStoreUpload))

    def testFileHash(self):
        instance = self.createMediaStoreUpload(self.test_files['test.png'])
        file_md5hash = instance.getFileHash()
        m = re.search('^[0-9a-f]{32}', file_md5hash)
        self.assertTrue(m)
        self.assertEqual(file_md5hash, m.group(0))

    def testImageDimensions(self):
        test_file = self.test_files['test.png']
        instance = self.createMediaStoreUpload(test_file)
        w, h = instance.getImageDimensions()
        actual = {'w':w, 'h':h}
        expected = test_file['dimensions']
        self.assertEqual(actual, expected)

    def testFileExtension(self):
        test_file = self.test_files['test.png']
        instance = self.createMediaStoreUpload(test_file)
        self.assertEqual(instance.getFileExtension(), test_file['extension'])

    def testFileType(self):
        test_file = self.test_files['test.png']
        instance = self.createMediaStoreUpload(test_file)
        self.assertEqual(instance.getFileType(), test_file['content-type'])

    def testFileSize(self):
        test_file = self.test_files['test.png']
        instance = self.createMediaStoreUpload(test_file)
        self.assertEqual(instance.getFileSize(), len(test_file['content']))

    def testCreateFileName(self):
        test_file = self.test_files['test.png']
        instance = self.createMediaStoreUpload(test_file)
        expected_filename = '%s.%s' % (instance.getFileHash(), instance.getFileExtension())
        self.assertEqual(instance.createFileName(), expected_filename)

    def testCreateMediaStoreInstance(self):
        test_file = self.test_files['test.png']
        media_store_upload = self.createMediaStoreUpload(test_file)
        media_store = media_store_upload.createInstance()
        self.assertEqual(media_store.file_name, media_store_upload.createFileName())
        self.assertEqual(media_store.file_size, media_store_upload.getFileSize())
        self.assertEqual(media_store.file_type, media_store_upload.getFileType())
        self.assertEqual(media_store.file_md5hash, media_store_upload.getFileHash())
        self.assertEqual(media_store.file_extension, media_store_upload.getFileExtension())

        w, h = media_store_upload.getImageDimensions()
        self.assertEqual(media_store.img_width, w)
        self.assertEqual(media_store.img_height, h)

    def testInstanceExists(self):
        test_file = self.test_files['test.png']
        media_store_upload = self.createMediaStoreUpload(test_file)

        self.assertFalse(media_store_upload.instanceExists())
        media_store = media_store_upload.createInstance()
        media_store.save()
        self.assertTrue(media_store_upload.instanceExists())
        media_store.delete()
        self.assertFalse(media_store_upload.instanceExists())

    def testGetInstance(self):
        test_file = self.test_files['test.png']
        media_store_upload = self.createMediaStoreUpload(test_file)
        with self.assertRaises(Exception) as context:
            media_store_upload.getInstance()
        self.assertTrue(isinstance(context.exception, MediaStore.DoesNotExist))

        media_store = media_store_upload.createInstance()
        media_store.save()

        found = media_store_upload.getInstance()
        self.assertEqual(found.pk, media_store.pk)
        found.delete()

    def testS3FileKey(self):
        test_file = self.test_files['test.png']
        media_store_upload = self.createMediaStoreUpload(test_file)
        media_store_upload.saveToBucket = MagicMock(return_value=True)

        with self.assertRaises(Exception) as context:
            media_store_upload.getS3FileKey()
        self.assertTrue(isinstance(context.exception, MediaStoreException))

        media_store = media_store_upload.save()
        self.assertTrue(media_store_upload.getS3FileKey())
        media_store.delete()

    def testSaveDoesNotExist(self):
        test_file = self.test_files['test.png']
        media_store_upload = self.createMediaStoreUpload(test_file)
        self.assertFalse(media_store_upload.instanceExists())
        media_store_upload.saveToBucket = MagicMock(return_value=True)
        media_store = media_store_upload.save()
        self.assertTrue(media_store)
        media_store_upload.saveToBucket.assert_called_once_with()
        media_store.delete()

    def testSaveDoesExist(self):
        test_file = self.test_files['test.png']
        m1 = self.createMediaStoreUpload(test_file)
        m1.saveToBucket = MagicMock(return_value=True)
        self.assertFalse(m1.instanceExists())
        r1 = m1.save()
        m1.saveToBucket.assert_called_once_with()

        m2 = self.createMediaStoreUpload(test_file)
        m2.saveToBucket = MagicMock(return_value=True)
        self.assertTrue(m2.instanceExists())
        r2 = m2.save()
        m2.saveToBucket.assert_not_called()

        self.assertEqual(r1.pk, r2.pk)
        r2.delete()

    def testInvalidExtension(self):
        test_file = self.test_files['test.badextension']
        media_store_upload = self.createMediaStoreUpload(test_file)
        self.assertFalse(media_store_upload.validateImageExtension())
        self.assertFalse(media_store_upload.isValid())

    def testInvalidImage(self):
        test_file = self.test_files['empty.jpg']
        media_store_upload = self.createMediaStoreUpload(test_file)
        self.assertFalse(media_store_upload.validateImageOpens())
        self.assertTrue(media_store_upload.validateImageExtension())
        self.assertFalse(media_store_upload.isValid())

    def testImageJpegExtensionNormalized(self):
        test_file = self.test_files['empty.jpeg']
        media_store_upload = self.createMediaStoreUpload(test_file)
        normalized_jpeg_extension = "jpg"
        self.assertEqual(media_store_upload.getFileExtension(), normalized_jpeg_extension)
        self.assertTrue(media_store_upload.validateImageExtension())

class TestUtilFunctions(unittest.TestCase):
    def testGuessImageExtensionFromUrl(self):
        def guess(url):
            ''' Short wrapper function, purely for convenience and concise asserts...'''
            return mediastore.guessImageExtensionFromUrl(url)
        self.assertEqual("jpeg", guess('https://example.com/profile_images/466953024271679488/3rftwYWT.jpeg'))
        self.assertEqual("jpg", guess('https://example.com/commons/thumb/c/c7/Harvard_square_harvard_yard.JPG/300px-Harvard_square_harvard_yard.JPG'))
        self.assertEqual("gif", guess('http://example.com/static/xyz/files/horizontal_large_nobg.gif?m=1489563850&_q=1'))
        self.assertEqual("png", guess('https://site.example.com/sites/default/files/_landing_carousel/Ext-538-carousel.png'))
        self.assertEqual(None, guess('http://static1.example.com/static/5581f1f1e4b0be63c4780f1a/t/5584a36c/?format=1500w'))

class TestUrlImport(unittest.TestCase):
    def mockFetchRemoteImage(self):
        '''
        Returns a function mocking mediastore.fetchRemoteImage()
        so that it always returns a dummy file.
        '''
        temp_image_file = tempfile.NamedTemporaryFile(mode='r')
        def mock_fetch(url):
            return temp_image_file
        return mock_fetch

    @patch('media_management_api.media_service.mediastore.fetchRemoteImage')
    def testProcessRemoteImages(self, mock_fetch):
        mock_fetch.return_value = self.mockFetchRemoteImage()
        request_data = {
            "items": [
                {"url": "http://example.com/logo.jpg", "title": "Logo"},
                {"url": "http://example.com/logo2.png", "title": "Logo2", "description": "Another logo"},
            ]
        }

        processed = mediastore.processRemoteImages(request_data['items'])
        self.assertTrue(processed is not None)
        self.assertEqual(len(processed), len(request_data['items']))
        for item in request_data['items']:
            url = item['url']
            self.assertTrue(url in processed)
            self.assertEqual(sorted(processed[url].keys()), ["data", "file"])
            expected_data = {"title": item["title"]}
            self.assertEqual(sorted(processed[url]["data"].keys()), ["description", "title"])
            self.assertEqual(processed[url]["data"]["title"], item["title"])
            if "description" in item:
                self.assertEqual(processed[url]["data"]["description"], item["description"])
            else:
                self.assertEqual(processed[url]["data"]["description"], "")

class TestZipUpload(unittest.TestCase):

    test_files = TEST_FILES

    @patch('zipfile.ZipFile')
    @patch('zipfile.is_zipfile')
    def testProcessFileUploads(self, mock_is_zipfile, mock_zip):
        testZip = MockZipFile()
        testZip.write(self.test_files['test.png']['filename'])
        testZip.write(self.test_files['empty.jpg']['filename'])

        files = [testZip]
        mock_zip.return_value = testZip
        mock_is_zipfile.return_value = True
        files = mediastore.processFileUploads(files)
        self.assertEqual(len(files), 2)
        self.assertNotIn(testZip, files)

        testZip.write('some_directory/')
        files = [testZip]
        files = mediastore.processFileUploads(files)
        self.assertEqual(len(files), 2)
        self.assertNotIn('some_directory/', files)

class MockZipFile:
    test_files = TEST_FILES

    def __init__(self):
        self.files = []
        self.content_type = "application/zip"
    def __iter__(self):
        return iter(self.files)
    def write(self, fname):
        self.files.append(fname)
    def namelist(self):
        names = []
        for name in self.files:
            names.append(name)
        return names
    def open(self, file):
        return self
    def read(self):
        return self.test_files['test.png']['content']
