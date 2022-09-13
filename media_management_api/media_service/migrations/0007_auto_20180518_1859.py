# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-05-18 18:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("media_service", "0006_collection_custom_iiif_canvas_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="collection",
            old_name="custom_iiif_canvas_id",
            new_name="iiif_custom_canvas_id",
        ),
        migrations.RenameField(
            model_name="collection",
            old_name="custom_iiif_manifest_url",
            new_name="iiif_custom_manifest_url",
        ),
        migrations.AddField(
            model_name="collection",
            name="iiif_source",
            field=models.CharField(
                choices=[(b"images", b"Your Images"), (b"manifest", b"IIIF Manifest")],
                default=b"images",
                max_length=100,
            ),
        ),
    ]
