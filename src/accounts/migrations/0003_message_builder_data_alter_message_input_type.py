# Generated by Django 5.1.9 on 2025-06-03 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_favoriteconversation'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='builder_data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='input_type',
            field=models.CharField(choices=[('text', 'Text'), ('image', 'Image'), ('builder', 'Builder')], max_length=10),
        ),
    ]
