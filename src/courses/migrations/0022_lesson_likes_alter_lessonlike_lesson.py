# Generated by Django 5.1.5 on 2025-02-21 22:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0021_lessonlike'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='likes',
            field=models.ManyToManyField(related_name='liked_lessons', through='courses.LessonLike', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='lessonlike',
            name='lesson',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_likes', to='courses.lesson'),
        ),
    ]
