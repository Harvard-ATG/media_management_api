from rest_framework.permissions import BasePermission, IsAuthenticated
from media_management_api.media_service.models import CourseUser

import logging
logger = logging.getLogger(__name__)

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

class IsCourseUserAuthenticated(BasePermission):
    def has_permission(self, request, view):
        '''Returns True if the user is authenticated, otherwise False.'''
        has_perm = bool(request.user and request.user.is_authenticated)
        logger.debug("user %s for request %s %s has_permission: %s" % (request.user.id, request.method, request.path, has_perm))
        return has_perm

    def has_object_permission(self, request, view, object):
        '''
        Returns True if the user is a superuser, otherwise it depends on the request method and
        whether the user is a member of the course and whether they are an admin or not in that course.
        '''
        if request.user.is_superuser or request.user.is_staff:
            return True

        # Allow members of the course to access any read-only or "safe" method
        # but require admin permission to make any changes (e.g. POST, PUT, PATCH, DELETE)
        user = request.user
        users_qs = CourseUser.objects.filter(user_profile=user.profile, course=object)
        has_perm = False
        if request.method in SAFE_METHODS:
            has_perm = users_qs.exists()
        else:
            has_perm = users_qs.filter(is_admin=True).exists()
        logger.debug("user %s for request %s %s has_object_permission: %s" % (request.user.id, request.method, request.path, has_perm))
        return has_perm


class ResourceEndpointPermission(IsCourseUserAuthenticated):
    def has_object_permission(self, request, view, obj):
        has_perm = super(ResourceEndpointPermission, self).has_object_permission(request, view, obj.course)
        return has_perm


class CollectionEndpointPermission(IsCourseUserAuthenticated):
    def has_object_permission(self, request, view, obj):
        has_perm = super(CollectionEndpointPermission, self).has_object_permission(request, view, obj.course)
        return has_perm


class CollectionResourceEndpointPermission(IsCourseUserAuthenticated):
    def has_object_permission(self, request, view, obj):
        has_perm = super(CollectionResourceEndpointPermission, self).has_object_permission(request, view, obj.collection.course)
        return has_perm
