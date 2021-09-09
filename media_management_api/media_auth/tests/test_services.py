from datetime import datetime, timedelta
import unittest
import jwt

from ..models import Application
from media_management_api.media_service.models import Course, CourseUser
from ..services import (
    get_client_key,
    has_required_data,
    decode_jwt,
    get_course_user
    )
from ..exceptions import InvalidTokenError

class JWTAuthTest(unittest.TestCase):

    def setUp(self):
        self.application = Application.objects.get_or_create(
            client_id="test",
            client_secret="secret"
        )

    def test_get_client_key(self):
        header = {"client_id": "test"}
        self.assertEqual(get_client_key(header), "secret")

    def test_get_client_key_no_client_id(self):
        header = {}
        self.assertEqual(get_client_key(header), False)

    def test_get_client_key_no_client_id(self):
        header = {"client_id": "does not exist"}
        self.assertEqual(get_client_key(header), False)

    def test_has_required_data(self):
        data_to_check_for = ("a", "b", "c")
        data_to_check_in = {"a":1, "b":1, "c":1, "d":1}
        self.assertEqual(has_required_data(data_to_check_in, data_to_check_for), True)

    def test_has_required_data_fail(self):
        data_to_check_for = ("a", "b", "c")
        data_to_check_in = {"a":1, "d":1}
        self.assertEqual(has_required_data(data_to_check_in, data_to_check_for), False)

    def test_decode_jwt(self):
        issued_at = datetime.utcnow()
        expiration = issued_at + timedelta(seconds=60)
        test_payload = {
            "iat": int(issued_at.timestamp()),
            "exp": int(expiration.timestamp()),
            "client_id": "test",
            "course_id": 178,
            "user_id": 12345,
            "course_permission": "read"
        }
        test_jwt = jwt.encode(test_payload, "secret", algorithm="HS256")
        decoded_jwt = decode_jwt(test_jwt)
        self.assertEqual(decoded_jwt, test_payload)

    def test_decode_jwt_missing_expiration(self):
        test_payload = {
            "iat": datetime.utcnow(),
            "client_id": "test",
            "course_id": 178,
            "user_id": 12345,
            "course_permission": "read"
        }
        test_jwt = jwt.encode(test_payload, "secret", algorithm="HS256")
        decoded_jwt = decode_jwt(test_jwt)
        self.assertEqual(decoded_jwt, False)

    def test_decode_jwt_expired(self):
        test_payload = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() - timedelta(seconds=120),
            "client_id": "test",
            "course_id": 178,
            "user_id": 12345,
            "course_permission": "read"
        }
        test_jwt = jwt.encode(test_payload, "secret", algorithm="HS256")
        decoded_jwt = decode_jwt(test_jwt)
        self.assertEqual(decoded_jwt, False)

    def test_decode_jwt_unregistered_client(self):
        test_payload = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "client_id": "not registered",
            "course_id": 178,
            "user_id": 12345,
            "course_permission": "read"
        }
        test_jwt = jwt.encode(test_payload, "secret", algorithm="HS256")
        decoded_jwt = decode_jwt(test_jwt)
        self.assertEqual(decoded_jwt, False)

    def test_decode_jwt_bad_secret(self):
        test_payload = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "client_id": "test",
            "course_id": 178,
            "user_id": 12345,
            "course_permission": "read"
        }
        test_jwt = jwt.encode(test_payload, "not the secret", algorithm="HS256")
        decoded_jwt = decode_jwt(test_jwt)
        self.assertEqual(decoded_jwt, False)

    def test_get_course_user(self):
        test_course = Course.objects.create(
            title="Test Course",
            sis_course_id="abc123",
            lti_context_id="unique_",
            lti_tool_consumer_instance_guid="together"
        )
        token = {
            "user_id": 12,
            "course_id": test_course.pk,
            "course_permission": "read"
        }
        course_user = get_course_user(token)
        verified_course_user = CourseUser.objects.get(course=test_course, user_profile=course_user.profile)
        self.assertEqual(course_user.profile.id, verified_course_user.user_profile_id)

    def test_get_course_user_course_does_not_exist(self):
        token = {
            "user_id": 12,
            "course_id": 12000301123,
            "course_permission": "read"
        }
        with self.assertRaises(InvalidTokenError):
            get_course_user(token)