# Generated by Django 3.0.14 on 2024-11-25 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0215_auto_20241125_0958'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adsnapshot',
            name='trade_amount_fiat',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=18),
        ),
        migrations.AlterField(
            model_name='adsnapshot',
            name='trade_ceiling_fiat',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=18),
        ),
        migrations.AlterField(
            model_name='adsnapshot',
            name='trade_floor_fiat',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=18),
        ),
    ]
