# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0004_auto_20151217_1837'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediastore',
            name='file_type',
            field=models.CharField(max_length=512, null=True),
        ),
    ]
