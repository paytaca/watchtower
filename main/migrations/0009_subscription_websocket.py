# Generated by Django 3.0.7 on 2021-04-22 03:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_recipient_valid'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='websocket',
            field=models.BooleanField(default=False),
        ),
    ]
