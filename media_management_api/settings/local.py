from logging.config import dictConfig

from .base import *  # NOQA
from .base import LOGGING

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "[::1]", "localhost", ".localhost"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# INSTALLED_APPS += ('debug_toolbar',)
# MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

# For Django Debug Toolbar:
INTERNAL_IPS = (
    "127.0.0.1",
    "10.0.2.2",
)
DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}

dictConfig(LOGGING)
