# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0002_auto_20160130_1747'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='metadata',
            field=models.TextField(default=b'[]', blank=True),
        ),
    ]
