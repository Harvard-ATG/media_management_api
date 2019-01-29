from media_management_api.media_service.models import CourseUser

import logging
logger = logging.getLogger(__name__)

class BaseCourseFilter(object):
    filter_key = "pk__in"
    def __init__(self, view):
        self.view = view

    def filter_queryset(self, queryset):
        user = self.view.request.user
        if user.is_superuser or user.is_staff:
            return queryset

        course_ids_queryset = CourseUser.get_course_ids_for_user(user.profile)
        course_ids = list(course_ids_queryset)
        filters = {self.filter_key:course_ids}
        logger.debug("Applying course filter to queryset: %s" % filters)

        return queryset.filter(**filters)

class CourseEndpointFilter(BaseCourseFilter):
    filter_key = "pk__in"

class CollectionEndpointFilter(BaseCourseFilter):
    filter_key = "course__pk__in"

class ResourceEndpointFilter(BaseCourseFilter):
    filter_key = "course__pk__in"

class CollectionResourceEndpointPermission(BaseCourseFilter):
    filter_key = "collection__course__pk__in"
