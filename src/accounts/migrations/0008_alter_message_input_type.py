# Generated by Django 5.1.9 on 2025-06-28 01:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_message_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='input_type',
            field=models.CharField(choices=[('text', 'Text'), ('image_upload', 'Image Upload')], max_length=15),
        ),
    ]
