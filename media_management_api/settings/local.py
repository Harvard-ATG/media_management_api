from .base import *
from logging.config import dictConfig

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#INSTALLED_APPS += ('debug_toolbar',)
#MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

# For Django Debug Toolbar:
INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

# CORS headers
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = (
        'x-requested-with',
        'X-File-Size',
        'content-type',
        'accept',
        'origin',
        'authorization',
        'x-csrftoken'
    )

# Logging

# Log to console instead of a file when running locally
LOGGING['handlers']['default'] = {
    'level': logging.DEBUG,
    'class': 'logging.StreamHandler',
    'formatter': 'simple',
}

dictConfig(LOGGING)
