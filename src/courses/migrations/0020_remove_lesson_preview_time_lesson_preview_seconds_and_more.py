# Generated by Django 5.1.5 on 2025-02-21 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0019_lesson_is_premium_lesson_preview_time'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lesson',
            name='preview_time',
        ),
        migrations.AddField(
            model_name='lesson',
            name='preview_seconds',
            field=models.PositiveIntegerField(default=0, help_text='Number of seconds available for preview (0 for no preview)'),
        ),
        migrations.AlterField(
            model_name='lesson',
            name='is_premium',
            field=models.BooleanField(default=True, help_text='If True, only premium users can access this video'),
        ),
    ]
