import logging

import jwt

from media_management_api.media_service.models import Course, CourseUser, UserProfile

from .exceptions import InvalidTokenError
from .models import Application

logger = logging.getLogger(__name__)


def get_client_key(header):
    try:
        return Application.objects.get(client_id=header["client_id"]).client_secret
    except (KeyError, Application.DoesNotExist):
        return False


def has_required_data(token, data):
    return all([k in token for k in data])


def decode_jwt(token):
    required_claims = ["iat", "exp", "user_id", "client_id"]
    algorithms = ["HS256"]
    leeway = 10

    def _decode_jwt(verify_signature=True, key=None):
        return jwt.decode(
            token,
            key,
            algorithms=algorithms,
            leeway=leeway,
            options={
                "verify_signature": verify_signature,
                "require": required_claims,
            },
        )

    # We only read the unverified token to get the "client_id" in order to successfully verify later.
    # A token should not be trusted until the signature is actually verified.
    try:
        unverified_token = _decode_jwt(verify_signature=False)
        key = get_client_key(unverified_token)
        if not key:
            logger.error(f"Client key not found for jwt: {token}")
            return False
        verified_token = _decode_jwt(verify_signature=True, key=key)
    except jwt.exceptions.InvalidTokenError as e:
        logger.error(f"Invalid token error: {e} jwt: {token}")
        return False

    return verified_token


def get_course_user(token):
    user = get_or_create_user(token["user_id"])
    add_user_to_course(
        user=user,
        course_id=token["course_id"],
        is_admin=token.get("course_permission") == "write",
    )
    return user


def get_or_create_user(user_id):
    user_profile = UserProfile.get_or_create_profile(user_id)
    return user_profile.user


def add_user_to_course(user=None, course_id=None, is_admin=False):
    try:
        course_user = CourseUser.add_user_to_course(
            user=user, course_id=course_id, is_admin=is_admin
        )
    except Course.DoesNotExist:
        raise InvalidTokenError("Course '%s' not found" % course_id)
    return course_user


def get_access_token_from_request(request, type_str):
    authorization = request.META.get("HTTP_AUTHORIZATION", "")
    if authorization.startswith(type_str):
        return authorization.replace(type_str, "")
    return None
