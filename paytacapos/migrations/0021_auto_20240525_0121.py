# Generated by Django 3.0.14 on 2024-05-25 01:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paytacapos', '0020_auto_20240223_0228'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='merchant',
            options={'ordering': ('-id',)},
        ),
        migrations.AddField(
            model_name='merchant',
            name='last_update',
            field=models.DateTimeField(null=True),
        ),
    ]
