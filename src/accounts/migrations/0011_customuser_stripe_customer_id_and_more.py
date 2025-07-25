# Generated by Django 5.1.9 on 2025-07-02 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_remove_creditpurchase_product_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='stripe_customer_id',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='membership',
            field=models.CharField(choices=[('FREE', 'Free'), ('PREMIUM', 'Premium')], default='FREE', max_length=10),
        ),
    ]
