# Generated by Django 3.0.14 on 2023-07-03 01:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0054_auto_20230626_1016'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='peer',
            name='is_arbiter',
        ),
    ]