from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from media_service.serializers import UserSerializer, GroupSerializer

def index(request):
    return HttpResponse('Login to the API <a href="%s">here</a>.<br>Browse the API <a href="%s">here</a>.' % (reverse('rest_framework:login'), reverse('api-root')))

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer