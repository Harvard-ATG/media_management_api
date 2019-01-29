from django.contrib.auth.models import User
from django.utils import timezone
from media_management_api.media_service.models import UserProfile, Course, CourseUser
from .models import Application, Token
from .exceptions import InvalidApplicationError, InvalidTokenError

import datetime
import logging

logger = logging.getLogger(__name__)

# Expiration time for tokens. Dictionary keys are intended
# to match the arguments accepted by datetime.timedelta():
#       https://docs.python.org/2/library/datetime.html#datetime.timedelta
TOKEN_EXPIRE = {"hours": 240}

# Token refresh time used when obtaining recent tokens to ensure that the token is good for _at least_ 24 hours
TOKEN_REFRESH = {"hours": 240 - 24}

def obtain_token(data):
    # Check that the required data are present
    required_data = ('client_id', 'client_secret', 'user_id')
    if not all([k in data for k in required_data]):
        raise InvalidApplicationError("Missing required data. Must include: %s" % ", ".join(required_data))

    # Validate the application
    application = None
    if is_valid_application(client_id=data['client_id'], client_secret=data['client_secret'], raise_exception=True):
        application = Application.objects.get(client_id=data['client_id'], client_secret=data['client_secret'])

     # Get or create a user profile
    if not data['user_id']:
        raise InvalidTokenError("Invalid user_id - must not be empty")
    user = get_or_create_user(data['user_id'])

    # Add the user to the specified course (this information is not saved in the token)
    course_id = data.get("course_id", None)
    course_permission = None
    if course_id:
        course_permission = data.get('course_permission', 'read')
        course_user = add_user_to_course(user=user, course_id=data['course_id'], is_admin=course_permission == 'write')

    # Try to reuse the most recent token for the user if it's still valid, otherwise
    # create a new token.
    token_attrs = {
        "user_profile": user.profile,
        "application": application,
    }
    recent_tokens = Token.objects.filter(**token_attrs).order_by('-created')[0:1]
    if len(recent_tokens) == 0 or is_token_expired(recent_tokens[0]) or is_token_refreshable(recent_tokens[0]):
        token = Token(**token_attrs)
        token.save()
    else:
        token = recent_tokens[0]

    # Return the token info
    token_expiration = get_token_expiration(token)
    token_response = {
        "user_id": data["user_id"],
        "access_token": token.key,
        "expires": token_expiration.strftime("%Y-%m-%d %H:%M:%S"),
        "course_id": course_id,
        "course_permission": course_permission
    }
    logger.debug("Obtained token: %s" % token_response)
    return token_response

def get_token(access_token):
    return Token.objects.get(key=access_token)

def get_token_expiration(token):
    return token.created + datetime.timedelta(**TOKEN_EXPIRE)

def get_token_refresh(token):
    return token.created + datetime.timedelta(**TOKEN_REFRESH)

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

def add_user_to_course(user=None, course_id=None, is_admin=False):
    try:
        course_user = CourseUser.add_user_to_course(user=user, course_id=course_id, is_admin=is_admin)
    except Course.DoesNotExist:
        raise InvalidTokenError("Course '%s' not found" % course_id)
    return course_user

def get_access_token_from_request(request):
    authorization = request.META.get('HTTP_AUTHORIZATION', '')
    access_token = None
    if authorization.lower().startswith("token "):
        access_token = authorization.split(" ", 2)[1]
    return access_token

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
                raise InvalidTokenError("Invalid token")
            return True

    now = timezone.now()
    expiration = get_token_expiration(token)
    if now > expiration:
        if raise_exception:
            logger.debug("Token %s expired at %s" % (token.pk, expiration))
            raise InvalidTokenError("Token has expired")
        return True
    return False

def is_token_refreshable(token):
    now = timezone.now()
    refresh = get_token_refresh(token)
    return now > refresh

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
