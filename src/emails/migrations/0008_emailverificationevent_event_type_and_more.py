# Generated by Django 5.1.5 on 2025-02-22 22:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0007_email_customer_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailverificationevent',
            name='event_type',
            field=models.CharField(choices=[('registration', 'Registration'), ('password_reset', 'Password Reset')], default='registration', max_length=50),
        ),
        migrations.AddField(
            model_name='emailverificationevent',
            name='metadata',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
