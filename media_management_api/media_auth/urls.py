from django.urls import path

from . import views

# Wire up our API using automatic URL routing.

app_name = "api-auth"

urlpatterns = [
    path("authorize-user", views.authorize_user, name="authorize-user"),
]
