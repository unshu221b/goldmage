# Generated by Django 5.1.9 on 2025-07-09 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_creditusagehistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='credits',
            field=models.IntegerField(default=50),
        ),
        migrations.AlterField(
            model_name='message',
            name='input_type',
            field=models.CharField(choices=[('text', 'Text'), ('image_upload', 'Image Upload'), ('social_link_upload', 'Social Link Upload')], max_length=20),
        ),
        migrations.AlterField(
            model_name='message',
            name='type',
            field=models.CharField(choices=[('builder', 'Builder'), ('creator', 'Creator'), ('editor', 'Editor'), ('analysis', 'Analysis'), ('system', 'System'), ('loading', 'Loading')], max_length=20),
        ),
    ]
