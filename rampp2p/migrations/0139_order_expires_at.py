# Generated by Django 3.0.14 on 2024-04-16 02:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0138_auto_20240415_0817'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='expires_at',
            field=models.DateTimeField(null=True),
        ),
    ]