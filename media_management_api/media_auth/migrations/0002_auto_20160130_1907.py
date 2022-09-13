# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("media_auth", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="application",
            old_name="code",
            new_name="key",
        ),
    ]
