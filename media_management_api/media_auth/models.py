import hashlib
import logging
import os

from django.db import models
from django.db.models import signals

logger = logging.getLogger(__name__)


class Application(models.Model):
    client_id = models.CharField(max_length=20, unique=True, blank=False)
    client_secret = models.CharField(max_length=40, blank=True)
    description = models.CharField(max_length=1024, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "application"
        verbose_name_plural = "applications"
        ordering = ["client_id"]


def generate_random_client_secret():
    """
    Returns a random hex string that can be used as the client secret.
    """
    m = hashlib.sha1()
    m.update(os.urandom(4096))
    return m.hexdigest()


def create_client_secret(sender, instance, **kwargs):
    """
    Sets a client secret for new Application instances (called via post_save signal).
    """
    if not instance.client_secret:
        instance.client_secret = generate_random_client_secret()
        instance.save(update_fields=["client_secret"])
        logger.debug(
            "Created client secret for sender=%s instance=%s client_secret=%s"
            % (sender, instance, instance.client_secret)
        )


signals.post_save.connect(create_client_secret, sender=Application)
