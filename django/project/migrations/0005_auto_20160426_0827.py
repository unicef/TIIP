# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-26 08:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0004_auto_20160406_1220'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coverage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('district', models.CharField(max_length=255)),
                ('clients', models.PositiveIntegerField()),
                ('health_workers', models.PositiveIntegerField()),
                ('facilities', models.PositiveIntegerField()),
                ('version', models.PositiveIntegerField(blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='project',
            name='clients',
        ),
        migrations.RemoveField(
            model_name='project',
            name='facilities',
        ),
        migrations.RemoveField(
            model_name='project',
            name='health_workers',
        ),
        migrations.AddField(
            model_name='coverage',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coverage', to='project.Project'),
        ),
    ]
