# Generated by Django 3.0.14 on 2024-11-20 01:38

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0195_mark_excess_ads_private_20241112_0053'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appversion',
            name='release_date',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.AlterUniqueTogether(
            name='appversion',
            unique_together={('platform', 'latest_version', 'min_required_version')},
        ),
    ]