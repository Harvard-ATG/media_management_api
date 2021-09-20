from rest_framework import authentication
from rest_framework import exceptions
from .services import (
    decode_jwt,
    get_access_token_from_request,
    )

from ..media_service.models import UserProfile

import logging
logger = logging.getLogger(__name__)


class CustomJWTAuthentication(authentication.BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer "
    
    def authenticate(self, request):
        jwt = get_access_token_from_request(request, "Bearer ")
        if not jwt:
            return None

        logger.debug(f"Attempting to authenticate jwt: {jwt}")
        decoded_token = decode_jwt(jwt)
        if not decoded_token:
            raise exceptions.AuthenticationFailed("JWT authentication failed")

        user = UserProfile.get_or_create_profile(decoded_token["user_id"]).user
        logger.debug(f"Authenticated user {user} with jwt: {jwt}")
        
        return (user, None)
