# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_service', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseimage',
            name='file_url',
            field=models.CharField(max_length=4096, null=True),
        ),
        migrations.AlterField(
            model_name='collectionimage',
            name='course_image',
            field=models.ForeignKey(related_name='collections', to='media_service.CourseImage'),
        ),
    ]
