from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
from .exceptions import InvalidTokenError
from .services import get_access_token_from_request, assert_token_valid, get_token

import logging
logger = logging.getLogger(__name__)

class CustomTokenAuthentication(authentication.BaseAuthentication):
    def authenticate_header(self, request):
        return 'Bearer realm="api"'
    
    def authenticate(self, request):
        access_token = get_access_token_from_request(request)
        if not access_token:
            return None

        try:
            assert_token_valid(access_token)
            token = get_token(access_token)
            user = token.user_profile.user
        except InvalidTokenError as e:
            logger.debug(str(e))
            raise exceptions.AuthenticationFailed(str(e))

        return (user, None)