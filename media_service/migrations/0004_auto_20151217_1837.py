# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0003_courseimage_is_upload'),
    ]

    operations = [
        migrations.RenameField(
            model_name='courseimage',
            old_name='file_url',
            new_name='img_url',
        ),
        migrations.RenameField(
            model_name='courseimage',
            old_name='original_file_name',
            new_name='upload_file_name',
        ),
        migrations.AddField(
            model_name='courseimage',
            name='img_height',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='courseimage',
            name='img_type',
            field=models.CharField(max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='courseimage',
            name='img_width',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='courseimage',
            name='thumb_height',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='courseimage',
            name='thumb_url',
            field=models.CharField(max_length=4096, null=True),
        ),
        migrations.AddField(
            model_name='courseimage',
            name='thumb_width',
            field=models.PositiveIntegerField(null=True),
        ),
    ]
