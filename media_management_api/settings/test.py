# For running unit tests
import os

from .local import *  # NOQA
from .local import BASE_DIR

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    },
}

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
}
