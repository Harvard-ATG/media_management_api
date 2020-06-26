from django.urls import path, include
from . import views 

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.

app_name = 'api-auth'

urlpatterns = [
    path('obtain-token/', views.obtain_token, name='obtain-token'),
    path('check-token/<str:access_token>/', views.check_token, name='check-token'),
    path('destroy-token/<str:access_token>/', views.destroy_token, name='destroy-token'),
]
