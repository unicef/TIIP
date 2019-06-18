# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-01-10 02:40
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0026_mapfile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='map_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}),
        ),
    ]
