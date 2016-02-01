# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_auth', '0002_auto_20160130_1907'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='application',
            options={'ordering': ['client_id'], 'verbose_name': 'application', 'verbose_name_plural': 'applications'},
        ),
        migrations.AlterModelOptions(
            name='token',
            options={'ordering': ['-created'], 'verbose_name': 'token', 'verbose_name_plural': 'tokens'},
        ),
        migrations.RemoveField(
            model_name='application',
            name='key',
        ),
        migrations.AddField(
            model_name='application',
            name='client_id',
            field=models.CharField(default='localhost', unique=True, max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='application',
            name='client_secret',
            field=models.CharField(max_length=40, blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='description',
            field=models.CharField(max_length=1024, blank=True),
        ),
        migrations.AlterField(
            model_name='token',
            name='key',
            field=models.CharField(unique=True, max_length=140),
        ),
    ]
