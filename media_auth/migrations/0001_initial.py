# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0002_auto_20160130_1747'),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=40, blank=True)),
                ('description', models.CharField(max_length=1024)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Token',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=40)),
                ('scope', models.CharField(max_length=1024, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(related_name='user_tokens', to='media_auth.Application')),
                ('user_profile', models.ForeignKey(related_name='user_tokens', to='media_service.UserProfile')),
            ],
        ),
    ]
