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
            name='Collection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('sort_order', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'collection',
                'verbose_name_plural': 'collections',
            },
            bases=(models.Model, media_service.models.SortOrderModelMixin),
        ),
        migrations.CreateModel(
            name='CollectionImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('sort_order', models.IntegerField(default=0)),
                ('collection', models.ForeignKey(related_name='images', to='media_service.Collection')),
            ],
            options={
                'verbose_name': 'collection_image',
                'verbose_name_plural': 'collection_images',
            },
            bases=(models.Model, media_service.models.SortOrderModelMixin),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('lti_context_id', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['title'],
                'verbose_name': 'course',
                'verbose_name_plural': 'courses',
            },
        ),
        migrations.CreateModel(
            name='CourseImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('original_file_name', models.CharField(max_length=4096, null=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('sort_order', models.IntegerField(default=0)),
                ('course', models.ForeignKey(related_name='images', to='media_service.Course')),
            ],
            options={
                'verbose_name': 'course_image',
                'verbose_name_plural': 'course_images',
            },
            bases=(models.Model, media_service.models.SortOrderModelMixin),
        ),
        migrations.CreateModel(
            name='MediaStore',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('file_name', models.CharField(max_length=1024)),
                ('file_size', models.PositiveIntegerField()),
                ('file_md5hash', models.CharField(max_length=32)),
                ('img_type', models.CharField(max_length=128, null=True)),
                ('img_width', models.PositiveIntegerField(null=True)),
                ('img_height', models.PositiveIntegerField(null=True)),
                ('reference_count', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'media_store',
                'verbose_name_plural': 'media_stores',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('lti_user_id', models.CharField(unique=True, max_length=1024, blank=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'user_profile',
                'verbose_name_plural': 'user_profiles',
            },
        ),
        migrations.AddField(
            model_name='courseimage',
            name='media_store',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='media_service.MediaStore', null=True),
        ),
        migrations.AddField(
            model_name='courseimage',
            name='owner',
            field=models.ForeignKey(to='media_service.UserProfile', null=True),
        ),
        migrations.AddField(
            model_name='collectionimage',
            name='course_image',
            field=models.ForeignKey(to='media_service.CourseImage'),
        ),
        migrations.AddField(
            model_name='collection',
            name='course',
            field=models.ForeignKey(related_name='collections', to='media_service.Course'),
        ),
    ]