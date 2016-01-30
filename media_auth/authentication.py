from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
from . import services

class CustomTokenAuthentication(authentication.BaseAuthentication):
    def authenticate_header(self, request):
        return 'Bearer realm="api"'
    
    def authenticate(self, request):
        access_token = services.get_access_token_from_request(request)
        if not access_token:
            return None

        try:
            services.is_token_valid(access_token, raise_exception=True)
            token = services.get_token(access_token)
            user = token.user_profile.user
        except services.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(str(e))

        return (user, None)