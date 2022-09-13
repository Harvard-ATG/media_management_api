import logging

from django.http import HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import services
from .exceptions import InvalidTokenError

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@csrf_exempt
def authorize_user(request):
    jwt = services.get_access_token_from_request(request, "Bearer ")
    if not jwt:
        logger.warning("JWT missing from authorization header")
        return HttpResponseBadRequest("Not able to get JWT from request")

    decoded_token = services.decode_jwt(jwt)
    if not decoded_token:
        logger.warning(f"JWT decode failed: {jwt}")
        return HttpResponseBadRequest("Unable to verify the JWT")

    if "course_id" not in decoded_token:
        logger.warning(f"JWT missing course_id: {decoded_token}")
        return HttpResponseBadRequest("Missing course ID from token")

    try:
        services.get_course_user(decoded_token)  # strange name for this function
    except InvalidTokenError:
        logger.warning("JWT failed to authorize user because course does not exist")
        return HttpResponseNotFound("Course not found")

    logger.info(f"Authorized user: {decoded_token}")
    return JsonResponse({"success": True})
