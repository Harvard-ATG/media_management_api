# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_auth', '0003_auto_20160201_1644'),
    ]

    operations = [
        migrations.AlterField(
            model_name='token',
            name='key',
            field=models.CharField(unique=True, max_length=80),
        ),
    ]
