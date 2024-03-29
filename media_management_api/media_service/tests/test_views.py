import csv
import io

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Collection, Course, CourseUser, UserProfile


class BaseApiTestCase(APITestCase):
    def _create_test_superuser(self):
        user_profile = UserProfile.get_or_create_profile("SuperUserTest")
        superuser = user_profile.user
        superuser.is_superuser = True
        superuser.save()
        return superuser

    def _create_test_nonsuperuser(self):
        user_profile = UserProfile.get_or_create_profile("NonSuperuserTest")
        nonsuperuser = user_profile.user
        nonsuperuser.is_superuser = False
        nonsuperuser.save()
        return nonsuperuser


class TestCourseEndpoint(BaseApiTestCase):
    fixtures = ["test.json"]

    def setUp(self):
        self.superuser = self._create_test_superuser()
        self.nonsuperuser = self._create_test_nonsuperuser()

    def get_example_item(self, detail=False):
        example_item = {
            "url": "http://localhost:8000/courses/1",
            "id": "1",
            "title": "Test",
            "collections_url": "http://localhost:8000/courses/1/collections",
            "images_url": "http://localhost:8000/courses/1/images",
            "lti_context_id": "asdf",
            "lti_tool_consumer_instance_guid": "asdf.canvas.localhost",
            "lti_tool_consumer_instance_name": "Localhost Instance",
            "lti_context_label": "Test",
            "lti_context_title": "Test",
            "sis_course_id": "sis123",
            "canvas_course_id": "canvas123",
            "created": "2015-12-15T15:42:33.443434Z",
            "updated": "2015-12-15T15:42:33.443434Z",
            "type": "courses",
        }
        if detail:
            example_item.update(
                {
                    "images": [
                        {
                            "url": "http://localhost:8000/course-images/1",
                            "id": 1,
                            "course_id": 1,
                            "title": "Example Image",
                            "description": "",
                            "metadata": "[]",
                            "sort_order": 0,
                            "original_file_name": None,
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
                            "thumb_url": None,
                            "iiif_base_url": None,
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
                            "iiif_source": "custom",
                            "iiif_images_manifest_url": "http://localhost:8000/iiif/manifest/1",
                            "iiif_images_canvas_id": "",
                            "iiif_custom_manifest_url": "https://iiif.harvardartmuseums.org/manifests/object/226092",
                            "iiif_custom_canvas_id": "https://iiif.harvardartmuseums.org/manifests/object/226092/annotation/anno-43183805",
                            "iiif_manifest": {
                                "url": "https://iiif.harvardartmuseums.org/manifests/object/226092",
                                "source": "custom",
                                "canvas_id": "https://iiif.harvardartmuseums.org/manifests/object/226092/annotation/anno-43183805",
                            },
                            "created": "2015-12-15T15:42:33.443434Z",
                            "updated": "2015-12-15T15:42:33.443434Z",
                            "type": "collections",
                        },
                    ],
                }
            )
        return example_item

    def test_course_list(self):
        self.client.force_authenticate(self.superuser)

        courses = Course.objects.all()
        url = reverse("api:course-list")
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
        self.client.force_authenticate(self.superuser)

        pk = 1
        url = reverse("api:course-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get an example response item
        example_item = self.get_example_item(detail=True)

        # Check course attributes
        nested_keys = ("images", "collections")
        course_keys = sorted([k for k in response.data if k not in nested_keys])
        expected_course_keys = sorted(
            [k for k in example_item.keys() if k not in nested_keys]
        )
        self.assertEqual(course_keys, expected_course_keys)
        self.assertTrue(all([k in response.data for k in nested_keys]))

        # Check nested items
        for nested_key in nested_keys:
            self.assertTrue(len(example_item[nested_key]) > 0)
            expected_image_keys = sorted(
                [k for k in example_item[nested_key][0].keys()]
            )
            for item in response.data[nested_key]:
                item_keys = sorted([k for k in item])
                self.assertEqual(item_keys, expected_image_keys)

    def test_create_course(self):
        self.client.force_authenticate(self.superuser)

        url = reverse("api:course-list")
        body = {
            "title": "Test Course",
            "lti_context_id": "e4d7f1b4ed2e42d15898f4b27b019da4",
            "lti_tool_consumer_instance_guid": "test.localhost",
        }

        # Create the new course
        response = self.client.post(url, body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the fields we submitted are reflected in a course object
        self.assertTrue("id" in response.data)
        self.assertTrue(Course.objects.filter(pk=response.data["id"]).exists())
        created_course = Course.objects.get(pk=response.data["id"])
        for f in body:
            self.assertEqual(response.data[f], body[f])
            self.assertEqual(getattr(created_course, f), body[f])

    def test_create_course_user_is_added_as_admin(self):
        self.client.force_authenticate(self.nonsuperuser)

        url = reverse("api:course-list")
        body = {
            "title": "Test Course",
            "lti_context_id": "e4d7f1b4ed2e42d15898f4b27b019da4",
            "lti_tool_consumer_instance_guid": "test.localhost",
        }

        # Create the new course
        response = self.client.post(url, body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue("id" in response.data)

        course_id = response.data["id"]
        self.assertTrue(Course.objects.filter(pk=course_id).exists())
        self.assertTrue(
            CourseUser.objects.filter(
                user_profile=self.nonsuperuser.profile,
                course_id=course_id,
                is_admin=True,
            ).exists()
        )

    def test_delete_course(self):
        self.client.force_authenticate(self.superuser)

        pk = 1
        url = reverse("api:course-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertTrue(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=pk).exists())

    def test_update_course(self):
        self.client.force_authenticate(self.superuser)

        pk = 1
        url = reverse("api:course-detail", kwargs={"pk": pk})
        body = {
            "title": "Title Updated(!)",
            "lti_context_id": "updated_context_id",
            "lti_tool_consumer_instance_guid": "updated_guid",
        }

        # Show that our update differs from the existing course object
        course_before_update = Course.objects.get(pk=pk)
        for f in body:
            self.assertNotEqual(getattr(course_before_update, f), body[f])

        # Do the update
        response = self.client.put(url, body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Show that the updates were returned in the response and
        # are reflected in the course object
        course_after_update = Course.objects.get(pk=pk)
        for f in body:
            self.assertEqual(response.data[f], body[f])
            self.assertEqual(getattr(course_after_update, f), body[f])

    def test_course_images_list(self):
        self.client.force_authenticate(self.superuser)

        pk = 1
        url = reverse("api:course-images", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]["url"], "http://testserver/api/images/1")

    def test_course_images_csv(self):
        self.client.force_authenticate(self.superuser)

        pk = 1
        url = reverse("api:course-images-csv", kwargs={"pk": pk})
        response = self.client.get(url)
        content = response.content.decode("utf-8")
        cvs_reader = csv.reader(io.StringIO(content))
        body = list(cvs_reader)
        headers = body.pop(0)
        index_of_url = headers.index("url")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["content-type"], "text/csv; charset=utf-8")
        self.assertEqual(body[0][index_of_url], "http://testserver/api/images/1")

    def test_add_collection_to_course(self):
        self.client.force_authenticate(self.superuser)

        pk = 1
        url = reverse("api:course-collections", kwargs={"pk": pk})
        body = {
            "title": "Test Collection",
            "description": "Some description",
        }

        # Create the new collection
        response = self.client.post(url, body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the fields we submitted are reflected in a course object
        self.assertTrue("id" in response.data)
        self.assertTrue(Collection.objects.filter(pk=response.data["id"]).exists())
        created_collection = Collection.objects.get(pk=response.data["id"])
        self.assertEqual(created_collection.course.pk, pk)
        for f in body:
            self.assertEqual(response.data[f], body[f])
            self.assertEqual(getattr(created_collection, f), body[f])

    def test_update_order_of_collections_in_course(self):
        self.client.force_authenticate(self.superuser)

        collections = Collection.objects.filter(course__pk=1).order_by("sort_order")
        original_order = [c.pk for c in collections]
        proposed_order = list(reversed(original_order))

        pk = 1
        url = reverse("api:course-collections", kwargs={"pk": pk})
        body = {"sort_order": proposed_order}
        response = self.client.put(url, body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        collections_after_update = Collection.objects.filter(course__pk=1).order_by(
            "sort_order"
        )
        updated_order = [c.pk for c in collections_after_update]
        self.assertEqual(updated_order, proposed_order)

    def test_invalid_update_sort_order(self):
        self.client.force_authenticate(self.superuser)

        collections = Collection.objects.filter(course__pk=1).order_by("sort_order")
        actual_order = [c.pk for c in collections]
        order_missing_one_collection = actual_order[1:]
        order_with_an_extra_collection = actual_order + [9999]

        pk = 1
        url = reverse("api:course-collections", kwargs={"pk": pk})
        invalid_data = [
            None,
            True,
            False,
            "1,2,3",
            {},
            {"sort_order": None},
            {"sort_order": "1,2,3"},
            {"sort_order": []},
            {"sort_order": order_missing_one_collection},
            {"sort_order": order_with_an_extra_collection},
        ]

        for data in invalid_data:
            response = self.client.put(url, data)
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TestCollectionEndpoint(BaseApiTestCase):
    fixtures = ["test.json"]

    def setUp(self):
        self.superuser = self._create_test_superuser()
        self.client.force_authenticate(self.superuser)

    def test_collection_list(self):
        collections = Collection.objects.all()
        url = reverse("api:collection-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(collections))

        # Example of what we would expect
        example_item = {
            "url": "http://localhost:8000/collections/1",
            "id": 1,
            "title": "Scrambled Eggs Super!",
            "description": "",
            "sort_order": 1,
            "course_id": 1,
            "course_image_ids": [1, 4],
            "images_url": "http://localhost:8000/collections/1/images",
            "iiif_source": "custom",
            "iiif_images_manifest_url": "http://localhost:8000/iiif/manifest/1",
            "iiif_images_canvas_id": "",
            "iiif_custom_manifest_url": "https://iiif.harvardartmuseums.org/manifests/object/226092",
            "iiif_custom_canvas_id": "https://iiif.harvardartmuseums.org/manifests/object/226092/annotation/anno-43183805",
            "iiif_manifest": {
                "url": "https://iiif.harvardartmuseums.org/manifests/object/226092",
                "source": "custom",
                "canvas_id": "https://iiif.harvardartmuseums.org/manifests/object/226092/annotation/anno-43183805",
            },
            "created": "2015-12-15T15:42:33.443434Z",
            "updated": "2016-01-06T21:13:08.353908Z",
            "type": "collections",
        }
        expected_keys = sorted(example_item.keys())
        for collection_data in response.data:
            actual_keys = sorted(collection_data.keys())
            self.assertEqual(actual_keys, expected_keys)

    def test_collection_detail(self):
        pk = 1
        url = reverse("api:collection-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get an example response item
        example_item = {
            "url": "http://localhost:8000/collections/1",
            "id": 1,
            "title": "Scrambled Eggs Super!",
            "description": "",
            "sort_order": 1,
            "course_id": 1,
            "course_image_ids": [1, 4],
            "images": [],
            "images_url": "http://localhost:8000/collections/1/images",
            "iiif_source": "custom",
            "iiif_images_manifest_url": "http://localhost:8000/iiif/manifest/1",
            "iiif_images_canvas_id": "",
            "iiif_custom_manifest_url": "https://iiif.harvardartmuseums.org/manifests/object/226092",
            "iiif_custom_canvas_id": "https://iiif.harvardartmuseums.org/manifests/object/226092/annotation/anno-43183805",
            "iiif_manifest": {
                "url": "https://iiif.harvardartmuseums.org/manifests/object/226092",
                "source": "custom",
                "canvas_id": "https://iiif.harvardartmuseums.org/manifests/object/226092/annotation/anno-43183805",
            },
            "created": "2015-12-15T15:42:33.443434Z",
            "updated": "2016-01-06T21:13:08.353908Z",
            "type": "collections",
        }
        expected_keys = sorted(example_item.keys())
        actual_keys = sorted(response.data.keys())
        self.assertEqual(actual_keys, expected_keys)

    def test_create_collection(self):
        url = reverse("api:collection-list")
        body = {
            "title": "Test Collection",
            "description": "Some description",
            "course_id": 1,
        }

        # Create the new collection
        response = self.client.post(url, body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the fields we submitted are reflected in a course object
        self.assertTrue("id" in response.data)
        self.assertTrue(Collection.objects.filter(pk=response.data["id"]).exists())
        created_collection = Collection.objects.get(pk=response.data["id"])
        for f in body:
            self.assertEqual(response.data[f], body[f])
            self.assertEqual(getattr(created_collection, f), body[f])

    def test_delete_collection(self):
        pk = 1
        url = reverse("api:collection-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertTrue(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Collection.objects.filter(pk=pk).exists())

    def test_update_collection(self):
        pk = 1
        url = reverse("api:collection-detail", kwargs={"pk": pk})
        collection = Collection.objects.get(pk=pk)
        body = {
            "title": "Thidwick The Big-Hearted Moose",
            "description": 'Thidwick the big-hearted moose is happy his antlers "can be of some use" to a menagerie of animals who move in and make themselves at home.',
            "course_id": collection.course.pk,
            "course_image_ids": [1, 2, 3, 4],
        }

        # Do the update
        response = self.client.put(url, body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Show that the updates were returned in the response and
        # are reflected in the course object
        collection_after_update = Collection.objects.get(pk=pk)
        for f in ("title", "description", "course_id"):
            self.assertEqual(response.data[f], body[f])

        course_image_ids = collection_after_update.resources.values_list(
            "resource__pk", flat=True
        )
        self.assertSequenceEqual(response.data["course_image_ids"], course_image_ids)
