from django.db import models
from django.db.models import signals
from media_management_api.media_service.models import UserProfile

import os
import base64
import struct
import hashlib
import logging

logger = logging.getLogger(__name__)

class Application(models.Model):
    client_id = models.CharField(max_length=20, unique=True, blank=False)
    client_secret = models.CharField(max_length=40, blank=True)
    description = models.CharField(max_length=1024, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'application'
        verbose_name_plural = 'applications'
        ordering = ["client_id"]

class Token(models.Model):
    key = models.CharField(max_length=80, unique=True, blank=False)
    scope = models.CharField(max_length=1024, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="user_tokens")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='user_tokens')

    class Meta:
        verbose_name = 'token'
        verbose_name_plural = 'tokens'
        ordering = ["-created"]

def generate_random_client_secret():
    '''
    Returns a random hex string that can be used as the client secret.
    '''
    m = hashlib.sha1()
    m.update(os.urandom(4096))
    return m.hexdigest()

def generate_random_access_token(pk):
    '''
    Returns a unique, non-guessable string that can be used as the access token.
    '''
    m = hashlib.sha1()
    m.update(os.urandom(4096))

    digest_encoded_bytes = base64.urlsafe_b64encode(m.digest())
    pk_encoded_bytes = base64.urlsafe_b64encode(struct.pack('I', int(pk))) # ensure uniqueness
    token = (digest_encoded_bytes + pk_encoded_bytes).strip(b"=\n").decode("utf-8")

    return token

def create_token_key(sender, instance, **kwargs):
    '''
    Sets an access token for new Token instances (called via post_save signal).
    '''
    if not instance.key:
        instance.key = generate_random_access_token(instance.pk)
        instance.save(update_fields=['key'])
        logger.debug("Creating token key for sender=%s instance=%s token=%s" % (sender, instance, instance.key))

def create_client_secret(sender, instance, **kwargs):
    '''
     Sets a client secret for new Application instances (called via post_save signal).
    '''
    if not instance.client_secret:
        instance.client_secret = generate_random_client_secret()
        instance.save(update_fields=['client_secret'])
        logger.debug("Created client secret for sender=%s instance=%s client_secret=%s" % (sender, instance, instance.client_secret))


signals.post_save.connect(create_client_secret, sender=Application)
signals.post_save.connect(create_token_key, sender=Token)
