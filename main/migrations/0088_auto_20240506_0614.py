# Generated by Django 3.0.14 on 2024-05-06 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0087_walletshard'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='walletshard',
            name='id',
        ),
        migrations.AlterField(
            model_name='walletshard',
            name='shard',
            field=models.CharField(max_length=350, primary_key=True, serialize=False),
        ),
    ]
