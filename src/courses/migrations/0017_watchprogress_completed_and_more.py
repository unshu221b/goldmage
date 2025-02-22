# Generated by Django 5.1.5 on 2025-02-19 02:43

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0016_lesson_duration_seconds'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='watchprogress',
            name='completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name='watchprogress',
            index=models.Index(fields=['-last_watched'], name='courses_wat_last_wa_a48430_idx'),
        ),
    ]
