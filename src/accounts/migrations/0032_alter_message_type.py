# Generated by Django 5.1.9 on 2025-07-21 17:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0031_alter_message_input_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='type',
            field=models.CharField(choices=[('initial_chat', 'Initial Chat'), ('chat', 'Chat'), ('booking', 'Booking'), ('system', 'System'), ('loading', 'Loading'), ('companion_cards', 'Companion Cards'), ('companion_cards_select', 'Companion Cards Select'), ('companion_cards_select_confirm', 'Companion Cards Select Confirm'), ('loading_companion_cards', 'Loading Companion Cards'), ('itinerary_summary', 'Itinerary Summary'), ('meetup_instructions', 'Meetup Instructions'), ('payment_response', 'Payment Response')], max_length=30),
        ),
    ]
