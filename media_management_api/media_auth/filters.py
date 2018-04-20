from .services import get_scope_from_request

import logging
logger = logging.getLogger(__name__)

class BaseEndpointFilter(object):
    filter_key = "pk__in"
    def __init__(self, view):
        self.view = view
        self.scope = get_scope_from_request(view.request)

    def filter_queryset(self, queryset):
        if self.scope is None:
            return queryset
        if self.scope['object'] == '*':
            return queryset
        object_ids = self.scope['object'].split(',')
        filters = {self.filter_key:object_ids}
        logger.debug("Filtering queryset with %s" % filters)
        return queryset.filter(**filters)

class CourseEndpointFilter(BaseEndpointFilter):
    filter_key = "pk__in"

class CollectionEndpointFilter(BaseEndpointFilter):
    filter_key = "course__pk__in"
        
class ResourceEndpointFilter(BaseEndpointFilter):
    filter_key = "course__pk__in"

class CollectionResourceEndpointPermission(BaseEndpointFilter):
    filter_key = "collection__course__pk__in"
