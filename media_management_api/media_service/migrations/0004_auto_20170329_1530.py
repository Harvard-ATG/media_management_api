# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import media_management_api.media_service.models


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0003_resource_metadata'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resource',
            old_name='upload_file_name',
            new_name='original_file_name',
        ),
        migrations.AlterField(
            model_name='resource',
            name='img_height',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='img_type',
            field=models.CharField(max_length=128, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='img_url',
            field=models.CharField(max_length=4096, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='img_width',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='metadata',
            field=models.TextField(default=media_management_api.media_service.models.metadata_default, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='thumb_height',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='thumb_url',
            field=models.CharField(max_length=4096, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='thumb_width',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]
