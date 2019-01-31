from rest_framework.permissions import BasePermission, IsAuthenticated
from media_management_api.media_service.models import CourseUser, UserProfile

import logging
logger = logging.getLogger(__name__)

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

class IsCourseUserAuthenticated(BasePermission):
    def has_permission(self, request, view):
        '''
        This is generally called by the check_permissions() method on an APIView to determine
        if a request should be permitted. It is called after authentication, but prior to invoking
        the method on the view.

        Returns True if the user is authenticated, otherwise False.
        '''
        has_perm = bool(request.user and request.user.is_authenticated)
        logger.debug("user %s has_permission for request %s %s => %s" % (request.user.id if request.user else None, request.method, request.path, has_perm))
        return has_perm

    def has_object_permission(self, request, view, object):
        '''
        This is generally called by the check_object_permissions() method on an APIView to determine
        if the request should be permitted for a given object.

        Note that this is not called automatically, unless the view is a GenericAPIView
        and the get_object() method is used.

        Returns True if the user has permission to modify the object, otherwise returns False.
        '''
        has_perm = self._has_object_permission(request, view, object)
        logger.debug("user %s has_object_permission for request %s %s => %s" % (request.user.id, request.method, request.path, has_perm))
        return has_perm

    def _has_object_permission(self, request, view, object):
        '''
        Returns True if the user is a superuser, otherwise it depends on the request method and
        whether the user is a member of the course and whether they are an admin or not in that course.
        '''
        user = request.user
        if user.is_superuser or user.is_staff:
            return True

        try:
            user_profile = user.profile
        except UserProfile.DoesNotExist:
            logger.exception("User profile missing for user: %s" % user)
            return False

        # Allow members of the course to access any read-only or "safe" method
        # but require admin permission to make any changes (e.g. POST, PUT, PATCH, DELETE)
        users_qs = CourseUser.objects.filter(user_profile=user_profile, course=object)
        has_perm = False
        if request.method in SAFE_METHODS:
            has_perm = users_qs.exists()
        else:
            has_perm = users_qs.filter(is_admin=True).exists()
        return has_perm
