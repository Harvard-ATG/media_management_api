from rest_framework import authentication
from rest_framework import exceptions
from .exceptions import InvalidTokenError
from .services import (
    decode_jwt,
    get_access_token_from_request,
    assert_token_valid,
    get_token,
    )

from ..media_service.models import UserProfile

import logging
logger = logging.getLogger(__name__)

class CustomTokenAuthentication(authentication.BaseAuthentication):
    def authenticate_header(self, request):
        return 'Token '
    
    def authenticate(self, request):
        access_token = get_access_token_from_request(request, "Token ")
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


class CustomJWTAuthentication(authentication.BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer "
    
    def authenticate(self, request):
        jwt = get_access_token_from_request(request, "Bearer ")

        if not jwt:
            return None

        decoded_token = decode_jwt(jwt)
        if not decoded_token:
            return None
        
        user = UserProfile.get_or_create_profile(decoded_token["user_id"]).user
        
        return (user, None)
