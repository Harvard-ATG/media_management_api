from .models import Course, CourseUser, UserProfile
from rest_framework.exceptions import APIException

import logging
logger = logging.getLogger(__name__)

class PrimaryKeyFilterBackend(object):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(pk=self.kwargs['pk'])

class IsCourseUserFilterBackend(object):
    def filter_queryset(self, request, queryset, view):
        user = request.user
        # Superuser and staff should not have any filter applied
        if user.is_superuser or user.is_staff:
            return queryset

        # Ensure that the user has a profile
        try:
            user_profile = user.profile
        except UserProfile.DoesNotExist:
            logger.exception("User profile missing for user: %s" % user)
            raise APIException("User profile missing")

        # Limit queryset to the courses that the user belongs to
        course_ids = CourseUser.get_course_ids_for_user(user_profile)
        filter_key = "pk__in"
        if hasattr(view, 'course_user_filter_key'):
            filter_key = view.course_user_filter_key
        filters = {filter_key:list(course_ids)}
        logger.debug("Filtering queryset: %s" % filters)

        return queryset.filter(**filters)
