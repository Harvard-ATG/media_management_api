from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate
from rest_framework.views import APIView

from media_management_api.media_service.models import Course, CourseUser, UserProfile
from media_management_api.media_service.permissions import IsCourseUserAuthenticated


class GenericPermissionView(APIView):
    permission_classes = [IsCourseUserAuthenticated]

    def get(self, request):
        return Response({})

    def post(self, request):
        return Response({})


class GenericCoursePermissionView(GenericAPIView):
    queryset = Course.objects.all()
    permission_classes = [IsCourseUserAuthenticated]

    def get(self, request, pk=None):
        course = (
            self.get_object()
        )  # expected to call check_object_permissions() implicitly
        return Response({"course_id": course.pk})

    def delete(self, request, pk=None):
        course = Course.objects.get(pk=pk)
        self.check_object_permissions(
            request, course
        )  # explicitly calling check_object_permissions()
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TestGenericUserHasPermission(APITestCase):
    def test_unauthenticated_request_is_forbidden(self):
        view = GenericPermissionView.as_view()
        request = APIRequestFactory().get("/")
        response = view(request)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_authenticated_request_is_allowed(self):
        user_profile = UserProfile.get_or_create_profile()
        view = GenericPermissionView.as_view()
        request = APIRequestFactory().get("/")
        force_authenticate(request, user=user_profile.user)
        response = view(request)
        self.assertEqual(status.HTTP_200_OK, response.status_code)


class TestGenericUserHasObjectPermission(APITestCase):
    def setUp(self):
        self.course = Course(title="TestCourse")
        self.course.save()
        self.guest_user_profile = UserProfile.get_or_create_profile("TestGuestUser")
        self.member_user_profile = UserProfile.get_or_create_profile("TestCourseUser")
        self.admin_user_profile = UserProfile.get_or_create_profile("TestCourseAdmin")
        CourseUser.add_to_course(
            is_admin=False,
            user_profile=self.member_user_profile,
            course_id=self.course.pk,
        )
        CourseUser.add_to_course(
            is_admin=True,
            user_profile=self.admin_user_profile,
            course_id=self.course.pk,
        )

        self.view = GenericCoursePermissionView.as_view()
        self.request_map = {
            "get": APIRequestFactory().get("/api-test/courses/%d" % self.course.pk),
            "delete": APIRequestFactory().delete(
                "/api-test/courses/%d" % self.course.pk
            ),
        }

    def tearDown(self):
        self.course.delete()

    def test_non_course_user_forbidden_for_all_requests(self):
        for method in self.request_map:
            request = self.request_map[method]
            force_authenticate(request, user=self.guest_user_profile.user)
            response = self.view(request, pk=self.course.pk)
            self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_course_admin_permitted_to_get_and_delete(self):
        request = self.request_map["get"]
        force_authenticate(request, user=self.admin_user_profile.user)
        response = self.view(request, pk=self.course.pk)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        request = self.request_map["delete"]
        force_authenticate(request, user=self.admin_user_profile.user)
        response = self.view(request, pk=self.course.pk)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

    def test_course_user_permitted_to_get_but_not_delete(self):
        request = self.request_map["get"]
        force_authenticate(request, user=self.member_user_profile.user)
        response = self.view(request, pk=self.course.pk)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        request = self.request_map["delete"]
        force_authenticate(request, user=self.member_user_profile.user)
        response = self.view(request, pk=self.course.pk)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
