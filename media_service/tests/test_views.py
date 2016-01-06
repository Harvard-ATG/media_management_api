from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from media_service.models import MediaStore, Course, Collection, CourseImage, CollectionImage

class TestCourseEndpoint(APITestCase):
    fixtures = ['test.json']

    def get_example_item(self, detail=False):
        example_item = {
            "url": "http://localhost:8000/courses/1",
            "id": "1",
            "title": "Test",
            "collections_url": "http://localhost:8000/courses/1/collections",
            "images_url": "http://localhost:8000/courses/1/images",
            "lti_context_id": "asdf",
            "lti_tool_consumer_instance_guid": "asdf.canvas.localhost",
            "created": "2015-12-15T15:42:33.443434Z",
            "updated": "2015-12-15T15:42:33.443434Z",
            "type": "courses",
        }
        if detail:
            example_item.update({
                "images": [
                    {
                        "url": "http://localhost:8000/course-images/1",
                        "upload_url": "http://localhost:8000/course-images/1/upload",
                        "id": 1,
                        "course_id": 1,
                        "title": "Example Image",
                        "description": "",
                        "sort_order": 0,
                        "upload_file_name": None,
                        "created": "2015-12-15T15:42:33.443434Z",
                        "updated": "2015-12-15T15:42:33.443434Z",
                        "type": "courseimages",
                        "is_upload": False,
                        "thumb_height": None,
                        "thumb_width": None,
                        "image_type": None,
                        "image_width": None,
                        "image_height": None,
                        "image_url": None,
                        "thumb_url": None
                    },
                ],
                "collections": [
                    {
                        "url": "http://localhost:8000/collections/1",
                        "id": 1,
                        "title": "Example Collection",
                        "description": "",
                        "sort_order": 1,
                        "course_id": 1,
                        "course_image_ids": [1],
                        "images_url": "http://localhost:8000/collections/1/images",
                        "created": "2015-12-15T15:42:33.443434Z",
                        "updated": "2015-12-15T15:42:33.443434Z",
                        "type": "collections"
                    },
                ],
            })
        return example_item

    def test_course_list(self):
        courses = Course.objects.all()
        url = reverse('course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(courses))
        
        # Example of what we would expect
        example_item = self.get_example_item()
        expected_keys = sorted(example_item.keys())
        for course_data in response.data:
            actual_keys = sorted(course_data.keys())
            self.assertEqual(actual_keys, expected_keys)
    
    def test_course_detail(self):
        pk = 1
        course = Course.objects.get(pk=pk)
        url = reverse('course-detail', kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get an example response item
        example_item = self.get_example_item(detail=True)
        expected_keys = sorted(example_item.keys())
        
        # Check course attributes
        nested_keys = ("images", "collections")
        course_keys = sorted([k for k in response.data if k not in nested_keys])
        expected_course_keys = sorted([k for k in example_item.keys() if k not in nested_keys])
        self.assertEqual(course_keys, expected_course_keys)
        self.assertTrue(all([ k in response.data for k in nested_keys ]))
        
        # Check nested items
        for nested_key in nested_keys:
            self.assertTrue(len(example_item[nested_key]) > 0)
            expected_image_keys = sorted([k for k in example_item[nested_key][0].keys()])
            for item in response.data[nested_key]:
                item_keys = sorted([k for k in item])
                self.assertEqual(item_keys, expected_image_keys)
    
class TestCollectionEndpoint(APITestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass

class TestCourseImageEndpoint(APITestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass

