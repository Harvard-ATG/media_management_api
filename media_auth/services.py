from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from media_service.models import UserProfile
from .models import Application, Token
from .exceptions import InvalidApplicationError, InvalidTokenError, InvalidScopeError

import datetime
import logging
import re

logger = logging.getLogger(__name__)

# Expiration time for tokens. Dictionary keys are intended
# to match the arguments accepted by datetime.timedelta():
#       https://docs.python.org/2/library/datetime.html#datetime.timedelta
TOKEN_EXPIRE = {"hours": 6}

# Token half-life used when obtaining recent tokens to provide a minimum valid time.
TOKEN_HALF_LIFE = {"hours": 3}

# Regex pattern to match token scope.
# Examples:
#   read:course:*       write:course:*
#   read:course:1       write:course:1
#   read:course:1,2,3   write:course:1,2,3
SCOPE_PATTERN = r'^(?P<permission>read|write):(?P<target>course):(?P<object>\*|\d+|(?:(?:\d+,)+\d+))$'


def obtain_token(data):
    # Check that the required data are present
    required_data = ('client_id', 'client_secret', 'user_id', 'scope')
    if not all([k in data for k in required_data]):
        raise InvalidApplicationError("Missing required data. Must include: %s" % ", ".join(required_data))
    
    # Validate the application
    application = None
    if is_valid_application(client_id=data['client_id'], client_secret=data['client_secret'], raise_exception=True):
        application = Application.objects.get(client_id=data['client_id'], client_secret=data['client_secret'])

    # Validate the scope
    scope = None
    if is_valid_scope(data['scope'], raise_exception=True):
        scope = data['scope']

     # Get the user object or create a new one if needed
    user = get_or_create_user(data['user_id'])

    # Try to reuse the most recent token for the user if it's still valid, otherwise
    # create a new token.
    token_attrs = {
        "scope": scope,
        "user_profile": user.profile,
        "application": application
    }
    recent_tokens = Token.objects.filter(**token_attrs).order_by('-created')[0:1]
    if len(recent_tokens) == 0 or is_token_expired(recent_tokens[0]) or is_token_past_half_life(recent_tokens[0]):
        token = Token(**token_attrs)
        token.save()
    else:
        token = recent_tokens[0]

    # Return the token info
    token_response = {
        "access_token": token.key,
        "scope": token.scope,
        "expires": TOKEN_EXPIRE.copy(),
        "scope": token.scope,
    }
    logger.debug("Obtained token: %s" % token_response)
    return token_response

def get_token(access_token):
    return Token.objects.get(key=access_token)

def get_token_expiration(token):
    return token.created + datetime.timedelta(**TOKEN_EXPIRE)

def get_token_half_life(token):
    return token.created + datetime.timedelta(**TOKEN_HALF_LIFE)

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

def assert_token_valid(token):
    return is_token_valid(token, raise_exception=True)

def is_token_valid(token, raise_exception=False):
    return not is_token_expired(token, raise_exception=raise_exception)

def is_token_expired(token, raise_exception=False):
    if not isinstance(token, Token):
        try:
            token = Token.objects.get(key=token)
        except Token.DoesNotExist:
            if raise_exception:
                raise InvalidTokenError("No such token: %s" % access_token)
            return True

    now = timezone.now()
    expiration = get_token_expiration(token)
    if now > expiration:
        if raise_exception:
            logger.debug("Token %s expired at %s" % (token.pk, expiration))
            raise InvalidTokenError("Token has expired")
        return True
    return False

def is_token_past_half_life(token):
    now = timezone.now()
    half_life = get_token_half_life(token)
    return now > half_life

def is_valid_application(client_id=None, client_secret=None, raise_exception=False):
    try:
        application = Application.objects.get(client_id=client_id, client_secret=client_secret)
    except Application.DoesNotExist:
        if raise_exception:
            raise InvalidApplicationError("Invalid application.")
        return False
    return True

def destroy_token(access_token):
    try:
        Token.objects.get(key=access_token).delete()
    except:
        return True
    return True

def get_access_token_from_request(request):
    authorization = request.META.get('HTTP_AUTHORIZATION', '')
    access_token = None
    if authorization.lower().startswith("token "):
        access_token = authorization.split(" ", 2)[1]
    return access_token

def get_scope_from_request(request):
    access_token = get_access_token_from_request(request)
    if access_token is None:
        return None

    token_attr = "_access_token"
    if hasattr(request, token_attr):
        token = getattr(request, token_attr, None)
    else:
        try:
            token = get_token(access_token)
        except:
            token = None
        setattr(request, token_attr, token)

    if token is None:
        return None
    return parse_scope(token.scope)

def is_valid_scope(scope, raise_exception=False):
    is_valid = bool(re.search(SCOPE_PATTERN, scope))
    if not is_valid and raise_exception:
        raise InvalidScopeError("Invalid scope.")
    return is_valid

def parse_scope(scope):
    match = re.search(SCOPE_PATTERN, scope)
    parsed = {k:match.group(k) for k in ['target', 'object', 'permission']}
    return parsed
