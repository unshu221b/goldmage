# Generated by Django 5.1.5 on 2025-02-18 20:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_watchprogress'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='duration_seconds',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
