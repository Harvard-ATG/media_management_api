from rest_framework.permissions import BasePermission
from .services import get_scope_from_request

import logging
logger = logging.getLogger(__name__)

READ_ONLY_METHODS = ('GET', 'HEAD', 'OPTIONS')
SCOPE_READ = "read"
SCOPE_WRITE = "write"

class BaseScopePermission(BasePermission):
    def __init__(self, *args, **kwargs):
        super(BaseScopePermission, self).__init__(*args, **kwargs)
        self.scope = None
        self.loaded_scope = False
    
    def has_permission(self, request, view):
        '''
        Implements has_permission().
        '''
        scope = self.get_scope_from_request(request)
        logger.debug("has_permission scope:%s" % scope)
        if scope is None:
            return True

        has_perm = self.has_scope_method_perm(request, view)
        logger.debug("has_permission:%s" % has_perm)
        return has_perm

    def has_object_permission(self, request, view, obj):
        '''
        Implements has_object_permission().
        '''
        scope = self.get_scope_from_request(request)
        logger.debug("has_object_permission scope:%s" % scope)
        if scope is None:
            return True

        has_method_perm = self.has_scope_method_perm(request, view)
        has_target_perm = self.has_scope_target_perm(request, view)
        has_object_perm = self.has_scope_object_perm(request, view, obj)
        
        has_perm = (has_method_perm and has_target_perm and has_object_perm)
        logger.debug("has_object_permission:%s (%s & %s & %s)" % (has_perm, has_method_perm, has_target_perm, has_object_perm))
        
        return has_perm

    def has_scope_method_perm(self, request, view):
        '''
        Utility method to check the request method type against the
        scope's permission (read or write).
        '''
        scope = self.get_scope_from_request(request)
        scope_perm = scope['permission']
        has_perm = False
        if scope_perm == SCOPE_WRITE:
            has_perm = True
        elif scope_perm == SCOPE_READ:
            has_perm = request.method in READ_ONLY_METHODS
        else:
            has_perm = False
        return has_perm

    def has_scope_target_perm(self, request, view):
        scope = self.get_scope_from_request(request)
        return scope['target'] == 'course'
    
    def has_scope_object_perm(self, request, view, obj):
        scope = self.get_scope_from_request(request)
        return scope['object'] == '*'
    
    def get_scope_from_request(self, request):
        if not self.loaded_scope:
            self.scope = get_scope_from_request(request)
            self.loaded_scope = True
        return self.scope

class CourseEndpointPermission(BaseScopePermission):
    """
    The request is authorized by the token scope.
    """
    def has_permission(self, request, view):
        scope = self.get_scope_from_request(request)
        has_perm = super(CourseEndpointPermission, self).has_permission(request, view)
        
        # Special case for creating a new course
        action = view.action_map.get(request.method.lower())
        if action == "create":
            has_perm = has_perm and (scope['object'] == '*')

        return has_perm
        
    def has_scope_object_perm(self, request, view, obj):
        scope = self.get_scope_from_request(request)
        has_perm = super(CourseEndpointPermission, self).has_scope_object_perm(request, view, obj)
        return has_perm or (str(scope['object']) == str(obj.pk))

class CollectionEndpointPermission(BaseScopePermission):
    """
    The request is authorized by the token scope.
    """
    def has_scope_object_perm(self, request, view, obj):
        scope = self.get_scope_from_request(request)
        has_perm = super(CollectionEndpointPermission, self).has_scope_object_perm(request, view, obj)
        return has_perm or (str(scope['object']) == str(obj.course.pk))

class ResourceEndpointPermission(CollectionEndpointPermission):
    """
    The request is authorized by the token scope.
    """
    pass

class CollectionResourceEndpointPermission(BaseScopePermission):
    """
    The request is authorized by the token scope.
    """
    def has_scope_object_perm(self, request, view, obj):
        scope = self.get_scope_from_request(request)
        has_perm = super(CollectionResourceEndpointPermission, self).has_scope_object_perm(request, view, obj)
        return has_perm or (str(scope['object']) == str(obj.collection.course.pk))
