# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0002_auto_20151217_1730'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseimage',
            name='is_upload',
            field=models.BooleanField(default=True),
        ),
    ]
