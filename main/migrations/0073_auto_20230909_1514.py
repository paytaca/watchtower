# Generated by Django 3.0.14 on 2023-09-09 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0072_auto_20230806_0014'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallethistory',
            name='amount',
            field=models.BigIntegerField(default=0),
        ),
    ]
