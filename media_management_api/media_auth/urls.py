from django.urls import path
from . import views 

# Wire up our API using automatic URL routing.

app_name = 'api-auth'

urlpatterns = [
    path("update-user", views.update_user, name="update-user"),
    path('obtain-token', views.obtain_token, name='obtain-token'),
    path('check-token/<str:access_token>', views.check_token, name='check-token'),
    path('destroy-token/<str:access_token>', views.destroy_token, name='destroy-token'),
]
