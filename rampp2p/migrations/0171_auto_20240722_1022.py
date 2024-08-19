# Generated by Django 3.0.14 on 2024-07-22 10:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0170_auto_20240719_1023'),
    ]

    operations = [
        migrations.AddField(
            model_name='arbiter',
            name='is_online',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='arbiter',
            name='last_online_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='peer',
            name='is_online',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='peer',
            name='last_online_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
