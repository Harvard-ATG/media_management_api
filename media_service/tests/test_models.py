# -*- coding: UTF-8 -*-
import unittest
import json
from media_service.models import MediaStore, Collection, Course, Resource, metadata_default

class TestMediaStore(unittest.TestCase):
    test_items = [
        {
            "file_name": "foo.jpg",
            "file_size": 51200,
            "file_md5hash": '4603090cae0c1ad78285207ffe9fb574',
            "file_extension": "jpg",
            "file_type": "image/jpeg",
            "img_width": 400,
            "img_height": 300,
        },
        {
            "file_name": "bar.gif",
            "file_size": 1024,
            "file_md5hash": '3213090cae0c1ad78285207ffe9fb456',
            "file_extension": "gif",
            "file_type": "image/gif",
            "img_width": 24,
            "img_height": 24,            
        }
    ]
    
    @classmethod
    def setUpClass(cls):
        for test_item in cls.test_items:
            instance = MediaStore(**test_item)
            instance.save()
            test_item['pk'] = instance.pk

    @classmethod
    def tearDownClass(cls):
        MediaStore.objects.filter(pk__in=[x['pk'] for x in cls.test_items]).delete()
 
    def test_get_image(self):
        queryset = MediaStore.objects.filter(pk__in=[x['pk'] for x in self.test_items])
        self.assertTrue(len(queryset) > 0)
        for media_store in queryset:
            full_actual = media_store.get_image_full()
            thumb_actual = media_store.get_image_thumb()
            thumb_w, thumb_h = media_store.calc_thumb_size()
            self.assertEqual(full_actual['width'], media_store.img_width)
            self.assertEqual(full_actual['height'], media_store.img_height)
            self.assertTrue(full_actual['url'])
            self.assertEqual(thumb_actual['width'], thumb_w)
            self.assertEqual(thumb_actual['height'], thumb_h)
            self.assertTrue(thumb_actual['url'])

class TestResource(unittest.TestCase):
    test_course = None
    
    @classmethod
    def setUpClass(cls):
        cls.test_course = Course(title="Test Course" , lti_context_id="ABC123", lti_tool_consumer_instance_guid="canvas")
        cls.test_course.save()

    def test_save_with_metadata(self):
        title = "Test Resource"
        course = TestResource.test_course
        default_metadata = metadata_default()
        missing_metadata = ["", None]
        invalid_metadata = [json.dumps(v) for v in None, True, False, 123, {}]
        valid_metadata = [json.dumps(v) for v in [], [{"label":"X", "value": "Y"}]]
        
        # check that missing or invalid metadata values are saved using the default value
        # for example the string "null" is not a valid value, so it should be overwritten with "[]"
        for metadata in missing_metadata + invalid_metadata:
            instance = Resource(course=course, title=title, metadata=metadata)
            instance.save()
            self.assertNotEqual(metadata, instance.metadata)
            self.assertEqual(default_metadata, instance.metadata)
        
        # check that valid metadata is saved unchanged
        for metadata in valid_metadata:
            instance = Resource(course=course, title=title, metadata=metadata)
            instance.save()
            self.assertEqual(metadata, instance.metadata)

class TestUnicodeInput(unittest.TestCase):
    
    def _createCourse(self, lti_context_id=None):
        course = Course(title="Test Course: %s" % lti_context_id, lti_context_id=lti_context_id, lti_tool_consumer_instance_guid="canavs")
        course.save()
        return course
    
    def test_collection_title(self):
        titles = [
            'My Awesome Collection',
             u'January is "январь" in Russian',
             u'New Year in Japanese: 新年',
             'Yet another awesome collection'
        ]
        course = self._createCourse(lti_context_id=1)
        
        for title in titles:
            collection = Collection(title=title, course=course)
            collection.save()
            self.assertEqual(collection.title, title)
            try:
                stringified_collection = str(collection)
            except UnicodeEncodeError as e:
                self.fail('Converting the collection object to a string raised UnicodeEncodeError: %s' % e)

