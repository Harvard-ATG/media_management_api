# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='collection',
            options={'ordering': ['course', 'sort_order', 'title'], 'verbose_name': 'collection', 'verbose_name_plural': 'collections'},
        ),
        migrations.AlterModelOptions(
            name='collectionresource',
            options={'ordering': ['collection', 'sort_order', 'resource'], 'verbose_name': 'collection resource', 'verbose_name_plural': 'collection resources'},
        ),
        migrations.AlterModelOptions(
            name='resource',
            options={'ordering': ['course', 'sort_order', 'title'], 'verbose_name': 'resource', 'verbose_name_plural': 'resources'},
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='lti_user_id',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='sis_user_id',
            field=models.CharField(max_length=60, unique=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='collectionresource',
            name='collection',
            field=models.ForeignKey(on_delete=models.CASCADE, related_name='resources', to='media_service.Collection'),
        ),
        migrations.AlterField(
            model_name='collectionresource',
            name='resource',
            field=models.ForeignKey(on_delete=models.CASCADE, related_name='collection_resources', to='media_service.Resource'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='course',
            field=models.ForeignKey(on_delete=models.CASCADE,related_name='resources', to='media_service.Course'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='owner',
            field=models.ForeignKey(on_delete=models.CASCADE, related_name='resources', blank=True, to='media_service.UserProfile', null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='user',
            field=models.OneToOneField(related_name='profile', null=True, on_delete=models.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
