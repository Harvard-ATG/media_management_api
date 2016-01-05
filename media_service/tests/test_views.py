from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from media_service.models import MediaStore, Course, Collection, CourseImage, CollectionImage

class TestCourseAPI(APITestCase):
    fixtures = ['test.json']
    def setUp(self):
        pass
    def tearDown(self):
        pass
    def test_course_list(self):
        url = reverse('course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        courses = Course.objects.all()
        self.assertEqual(len(response.data), len(courses))
    
class TestCollectionAPI(APITestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass

class TestCourseImageAPI(APITestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass

