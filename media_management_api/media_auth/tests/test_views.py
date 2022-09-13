from datetime import datetime, timedelta

import jwt
from django.test import TestCase

from media_management_api.media_service.models import Course, CourseUser, UserProfile

from ..models import Application


class TestAuthViews(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Tylor's test course")
        self.application = Application.objects.get_or_create(
            client_id="test", client_secret="secret"
        )

    def test_update_user_with_new_user(self):
        test_payload = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "client_id": "test",
            "course_id": self.course.pk,
            "user_id": 9999,
            "course_permission": "read",
        }
        test_jwt = jwt.encode(test_payload, "secret", algorithm="HS256")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {test_jwt}"}
        response = self.client.post("/api/auth/authorize-user", **headers)
        self.assertEqual(response.status_code, 200)
        updated_user = UserProfile.objects.get(sis_user_id=9999)
        course_user = CourseUser.objects.get(
            course=self.course, user_profile=updated_user
        )
        self.assertEqual(course_user.course.pk, self.course.pk)
        self.assertEqual(course_user.is_admin, False)

    def test_update_user_write_permission(self):
        write_payload = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "client_id": "test",
            "course_id": self.course.pk,
            "user_id": 9999,
            "course_permission": "write",
        }
        write_jwt = jwt.encode(write_payload, "secret", algorithm="HS256")
        write_headers = {"HTTP_AUTHORIZATION": f"Bearer {write_jwt}"}
        self.client.post("/api/auth/authorize-user", **write_headers)
        updated_user = UserProfile.objects.get(sis_user_id=9999)
        course_user = CourseUser.objects.get(
            course=self.course, user_profile=updated_user
        )
        self.assertEqual(course_user.is_admin, True)

    def test_update_user_course_does_not_exist(self):
        payload = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "client_id": "test",
            "course_id": 5,
            "user_id": 9999,
            "course_permission": "read",
        }
        test_jwt = jwt.encode(payload, "secret", algorithm="HS256")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {test_jwt}"}
        response = self.client.post("/api/auth/authorize-user", **headers)
        # JWT is valid, but course does not exist, so return 404
        self.assertEqual(response.status_code, 404)

    def test_update_user_payload_missing_user_id(self):
        payload = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "client_id": "test",
        }
        test_jwt = jwt.encode(payload, "secret", algorithm="HS256")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {test_jwt}"}
        response = self.client.post("/api/auth/authorize-user", **headers)
        # user_id is missing, so it is a bad request
        self.assertEqual(response.status_code, 400)
