# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings
import media_service.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('basemodel_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='media_service.BaseModel')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'collection',
                'verbose_name_plural': 'collections',
            },
            bases=('media_service.basemodel', media_service.models.SortOrderModelMixin),
        ),
        migrations.CreateModel(
            name='CollectionItem',
            fields=[
                ('basemodel_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='media_service.BaseModel')),
                ('collection', models.ForeignKey(to='media_service.Collection')),
            ],
            options={
                'verbose_name': 'collection_item',
                'verbose_name_plural': 'collection_items',
            },
            bases=('media_service.basemodel', media_service.models.SortOrderModelMixin),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('basemodel_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='media_service.BaseModel')),
                ('title', models.CharField(max_length=255)),
                ('lti_context_id', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['title'],
                'verbose_name': 'course',
                'verbose_name_plural': 'courses',
            },
            bases=('media_service.basemodel',),
        ),
        migrations.CreateModel(
            name='CourseMedia',
            fields=[
                ('basemodel_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='media_service.BaseModel')),
                ('original_file_name', models.CharField(max_length=4096, null=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('course', models.ForeignKey(to='media_service.Course')),
            ],
            options={
                'verbose_name': 'course_media',
                'verbose_name_plural': 'course_media',
            },
            bases=('media_service.basemodel', media_service.models.SortOrderModelMixin),
        ),
        migrations.CreateModel(
            name='MediaStore',
            fields=[
                ('basemodel_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='media_service.BaseModel')),
                ('file_name', models.CharField(max_length=1024)),
                ('file_size', models.PositiveIntegerField()),
                ('file_md5hash', models.CharField(max_length=32)),
                ('img_type', models.CharField(max_length=128, null=True)),
                ('img_width', models.PositiveIntegerField(null=True)),
                ('img_height', models.PositiveIntegerField(null=True)),
                ('reference_count', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'mediastore',
                'verbose_name_plural': 'mediastores',
            },
            bases=('media_service.basemodel',),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('basemodel_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='media_service.BaseModel')),
                ('lti_user_id', models.CharField(unique=True, max_length=1024, blank=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'user_profile',
                'verbose_name_plural': 'user_profiles',
            },
            bases=('media_service.basemodel',),
        ),
        migrations.AddField(
            model_name='coursemedia',
            name='media_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='media_service.MediaStore', null=True),
        ),
        migrations.AddField(
            model_name='coursemedia',
            name='owner',
            field=models.ForeignKey(to='media_service.UserProfile', null=True),
        ),
        migrations.AddField(
            model_name='collectionitem',
            name='course_media',
            field=models.ForeignKey(to='media_service.CourseMedia'),
        ),
        migrations.AddField(
            model_name='collection',
            name='course',
            field=models.ForeignKey(to='media_service.Course'),
        ),
    ]
