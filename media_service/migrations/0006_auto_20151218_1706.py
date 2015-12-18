# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0005_mediastore_file_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mediastore',
            name='img_type',
        ),
        migrations.AddField(
            model_name='mediastore',
            name='file_extension',
            field=models.CharField(max_length=6, null=True),
        ),
    ]
