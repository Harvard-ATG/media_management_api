from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from . import services
from .exceptions import MediaAuthException

import json
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
@csrf_exempt
def obtain_token(request):
    if not request.is_secure() and settings.DEBUG is not True:
        return HttpResponseBadRequest("Token request must be made over SSL!")
    if request.META['CONTENT_TYPE'] != 'application/json':
        return HttpResponseBadRequest("CONTENT_TYPE must be 'application/json'")

    data = None
    try:
        data = json.loads(request.body)
        logger.debug("Request to obtain token given data: %s" % data)
    except Exception as e:
        errstr = "Error parsing request to obtain token: %s. Error: %s" % (request.body, str(e))
        logger.error(errstr)
        return HttpResponseBadRequest(errstr)

    try:
        token = services.obtain_token(data)
    except MediaAuthException as e:
        logger.debug(e.as_json())
        return HttpResponseBadRequest(e.as_json())
    

    token_json = json.dumps(token)
    return HttpResponse(content=token_json, content_type="application/json")

@login_required
@user_passes_test(lambda u: u and u.is_superuser)
def check_token(request, access_token):
    msg = "VALID"
    status = 200
    if services.is_token_expired(access_token):
        status = 404
        msg = "INVALID"
    return HttpResponse(msg, status=status)

@login_required
@user_passes_test(lambda u: u and u.is_superuser)
def destroy_token(request, access_token):
    services.destroy_token(access_token)
    return HttpResponse("Deleted token:%s" % (access_token))
