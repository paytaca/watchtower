# Generated by Django 3.0.14 on 2024-05-08 06:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0151_auto_20240508_0623'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymenttype',
            name='short_name',
            field=models.CharField(default='', max_length=50, null=True),
        ),
    ]
