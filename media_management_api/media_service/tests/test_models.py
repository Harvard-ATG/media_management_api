# -*- coding: UTF-8 -*-
import unittest
import json

from media_management_api.media_service import models

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
            instance = models.MediaStore(**test_item)
            instance.save()
            test_item['pk'] = instance.pk

    @classmethod
    def tearDownClass(cls):
        models.MediaStore.objects.filter(pk__in=[x['pk'] for x in cls.test_items]).delete()

    def test_get_image(self):
        queryset = models.MediaStore.objects.filter(pk__in=[x['pk'] for x in self.test_items])
        self.assertTrue(len(queryset) > 0)
        for media_store in queryset:
            full_actual = media_store.get_iiif_full_url(thumb=False)
            thumb_actual = media_store.get_iiif_full_url(thumb=True)
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
        cls.test_course = models.Course(title="Test Course" , lti_context_id="ABC123", lti_tool_consumer_instance_guid="canvas")
        cls.test_course.save()

    def test_save_with_metadata(self):
        title = "Test Resource"
        course = TestResource.test_course
        default_metadata = models.metadata_default()
        missing_metadata = ("", None)
        invalid_metadata = (None, True, False, 123, {})
        valid_metadata = ([], [{"label":"X", "value": "Y"}])

        # check that missing or invalid metadata values are saved using the default value
        # for example the string "null" is not a valid value, so it should be overwritten with "[]"
        for metadata in missing_metadata + invalid_metadata:
            instance = models.Resource(course=course, title=title, metadata=metadata)
            instance.save()
            self.assertNotEqual(metadata, instance.metadata)
            self.assertEqual(default_metadata, instance.metadata)

        # check that valid metadata is saved unchanged
        for metadata in valid_metadata:
            instance = models.Resource(course=course, title=title, metadata=json.dumps(metadata))
            instance.save()
            self.assertEqual(json.dumps(metadata), instance.metadata)

class TestUnicodeInput(unittest.TestCase):

    def _createCourse(self, lti_context_id=None):
        course = models.Course(title="Test Course: %s" % lti_context_id, lti_context_id=lti_context_id, lti_tool_consumer_instance_guid="canavs")
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
            collection = models.Collection(title=title, course=course)
            collection.save()
            self.assertEqual(collection.title, title)
            try:
                stringified_collection = str(collection)
            except UnicodeEncodeError as e:
                self.fail('Converting the collection object to a string raised UnicodeEncodeError: %s' % e)


class TestCourseUser(unittest.TestCase):
    def setUp(self):
        self.courses = []
        for n in range(3):
            course = models.Course(title="TestCourse%d" % n)
            course.save()
            self.courses.append(course)

        self.user_profiles = []
        for n in range(3):
            user_profile = models.UserProfile()
            user_profile.save()
            self.user_profiles.append(user_profile)

        # Only one user in first course
        models.CourseUser(course=self.courses[0], user_profile=self.user_profiles[0], is_admin=True).save()

        # Two users in second course
        models.CourseUser(course=self.courses[1], user_profile=self.user_profiles[0], is_admin=False).save()
        models.CourseUser(course=self.courses[1], user_profile=self.user_profiles[1], is_admin=True).save()

        # Three users in third course
        models.CourseUser(course=self.courses[2], user_profile=self.user_profiles[0], is_admin=False).save()
        models.CourseUser(course=self.courses[2], user_profile=self.user_profiles[1], is_admin=False).save()
        models.CourseUser(course=self.courses[2], user_profile=self.user_profiles[2], is_admin=True).save()


    def test_get_course_ids_for_user(self):
        expected = [c.pk for c in self.courses]
        self.assertEqual(expected, models.CourseUser.get_course_ids(self.user_profiles[0]))

        expected = [self.courses[1].pk, self.courses[2].pk]
        self.assertEqual(expected, models.CourseUser.get_course_ids(self.user_profiles[1]))

        expected = [self.courses[2].pk]
        self.assertEqual(expected, models.CourseUser.get_course_ids(self.user_profiles[2]))

    def test_add_to_course(self):
        user_profile = models.UserProfile()
        user_profile.save()
        course_user = models.CourseUser.add_to_course(user_profile=user_profile, course_id=self.courses[0].pk, is_admin=True)

        self.assertTrue(models.CourseUser.objects.filter(user_profile=user_profile, course=self.courses[0], is_admin=True).exists())
        self.assertEqual(user_profile.pk, course_user.user_profile.pk)
        self.assertEqual(self.courses[0].pk, course_user.course.pk)
        self.assertTrue(course_user.is_admin)
