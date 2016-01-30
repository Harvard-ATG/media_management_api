from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from . import services

import json
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
@csrf_exempt
def create_token(request):
    if not request.is_secure() and settings.DEBUG is not True:
        return HttpResponseBadRequest("Token request must be made over SSL!")
    if request.META['CONTENT_TYPE'] != 'application/json':
        return HttpResponseBadRequest("CONTENT_TYPE must be 'application/json'")

    data = None
    try:
        data = json.loads(request.body)
        logger.debug("Request to create token given data: %s" % data)
    except Exception as e:
        errstr = "Error parsing request to create token: %s. Error: %s" % (request.body, str(e))
        logger.error(errstr)
        return HttpResponseBadRequest(errstr)

    try:
        token = services.create_token(data)
    except services.InvalidApplicationError as e:
        errstr = str(e)
        return HttpResponseBadRequest(errstr)

    token_json = json.dumps(token)
    return HttpResponse(content=token_json, content_type="application/json")

@login_required
@user_passes_test(lambda u: u and u.is_superuser)
def check_token(request, token_key):
    msg = "VALID"
    status = 200
    if services.is_token_expired(token_key):
        status = 404
        msg = "INVALID"
    return HttpResponse(msg, status=status)

@login_required
@user_passes_test(lambda u: u and u.is_superuser)
def destroy_token(request, token_key):
    services.destroy_token(token_key)
    return HttpResponse("Deleted token key:%s" % (token_key))
