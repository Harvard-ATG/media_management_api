from django.db import models
from django.db.models import signals
from media_service.models import UserProfile
import uuid
import hashlib
import logging

logger = logging.getLogger(__name__)

class Application(models.Model):
    key = models.CharField(max_length=40, unique=True, blank=True)
    description = models.CharField(max_length=1024, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

class Token(models.Model):
    key = models.CharField(max_length=40, unique=True, blank=False)
    scope = models.CharField(max_length=1024, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="user_tokens")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='user_tokens')

def create_instance_key(sender, instance, **kwargs):
    if not instance.key:
        logger.debug("Creating key for sender=%s instance=%s" % (sender, instance))
        m = hashlib.sha1()
        m.update(str(instance.id) + str(uuid.uuid4().get_hex().upper()))
        instance.key = m.hexdigest()
        instance.save(update_fields=['key'])
    
signals.post_save.connect(create_instance_key, sender=Application)
signals.post_save.connect(create_instance_key, sender=Token)