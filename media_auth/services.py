from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from media_service.models import UserProfile
from .models import Application, Token

import datetime
import logging

logger = logging.getLogger(__name__)

TOKEN_EXPIRE = {"minutes": 1}

class InvalidApplicationError(Exception):
    pass

class InvalidTokenError(Exception):
    pass

def create_token(data):
    # Check that the required data are present
    required_data = ('application_key', 'user_id', 'scope')
    if not all([k in data for k in required_data]):
        raise InvalidApplicationError("Missing required data. Must include: %s" % ", ".join(required_data))
    
    # Validate the application
    application = None
    if is_valid_application(data['application_key'], raise_exception=True):
        application = Application.objects.get(key=data['application_key'])

     # Get the user object or create a new one if needed
    user = get_or_create_user(data['user_id'])
    
    # Use the scope as-is
    scope = data['scope']

    # Try to reuse the most recent token for the user if it's still valid, otherwise
    # create a new token.
    token_attrs = {
        "scope": scope,
        "user_profile": user.profile,
        "application": application
    }
    recent_tokens = Token.objects.filter(**token_attrs).order_by('created')[0:1]
    if len(recent_tokens) == 0 or is_token_expired(recent_tokens[0]):
        token = Token(**token_attrs)
        token.save()
    else:
        token = recent_tokens[0]

    # Return the token info
    result = {
        "access_token": token.key,
        "scope": token.scope,
        "created": token.created.isoformat(),
    }
    logger.debug("Created token: %s" % result)
    return result

def get_token(token_key):
    return Token.objects.get(key=token_key)

def get_or_create_user(user_id):
    user_profiles = UserProfile.objects.filter(sis_user_id=user_id)
    user_profile = None
    if len(user_profiles) == 0:
        user_profile = UserProfile(sis_user_id=user_id)
        user_profile.save()
    else:
        user_profile = user_profiles[0]
    if not user_profile.user:
        user = User.objects.create_user(username="UserProfile:%s" % user_profile.id, password=None)
        user_profile.user = user
        user_profile.save()
    return user_profile.user

def is_token_valid(token, raise_excetion=False):
    return is_token_expired(token, raise_exception=raise_exception)

def is_token_expired(token, raise_exception=False):
    if isinstance(token, Token):
        token_key = token.key
    else:
        token_key = token

    try:
        token = Token.objects.get(key=token_key)
    except Token.DoesNotExist:
        if raise_exception:
            raise InvalidTokenError("No token exists with key %s" % token_key)
        return True

    created = token.created
    now = timezone.now()
    expiration = created + datetime.timedelta(**TOKEN_EXPIRE)
    if now > expiration:
        if raise_exception:
            raise InvalidTokenError("Token has expired. Expired at: %s" % expiration)
        return True

    return False

def is_valid_application(application_key, raise_exception=False):
    try:
        application = Application.objects.get(key=application_key)
    except Application.DoesNotExist:
        if raise_exception:
            raise InvalidApplicationError("Invalid application_key: %s" % application_key)
        return False
    return True

def destroy_token(token_key):
    try:
        Token.objects.get(key=token_key).delete()
    except:
        return True
    return True

def get_access_token_from_request(request):
    authorization = request.META.get('AUTHORIZATION', '')
    access_token = None
    if authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 2)[1]
    return access_token
