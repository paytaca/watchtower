# Generated by Django 3.0.14 on 2024-01-10 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0097_auto_20240110_0847'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ad',
            name='time_duration_choice',
            field=models.IntegerField(choices=[(1, '1 minute'), (5, '5 minutes'), (15, '15 minutes'), (30, '30 minutes'), (60, '1 hour'), (300, '5 hours'), (720, '12 hours'), (1440, '1 day')]),
        ),
        migrations.AlterField(
            model_name='adsnapshot',
            name='time_duration_choice',
            field=models.IntegerField(choices=[(1, '1 minute'), (5, '5 minutes'), (15, '15 minutes'), (30, '30 minutes'), (60, '1 hour'), (300, '5 hours'), (720, '12 hours'), (1440, '1 day')]),
        ),
        migrations.AlterField(
            model_name='order',
            name='time_duration_choice',
            field=models.IntegerField(choices=[(1, '1 minute'), (5, '5 minutes'), (15, '15 minutes'), (30, '30 minutes'), (60, '1 hour'), (300, '5 hours'), (720, '12 hours'), (1440, '1 day')]),
        ),
    ]
