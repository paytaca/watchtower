# Generated by Django 3.0.14 on 2023-09-06 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paytacapos', '0014_merchant_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='merchant',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='merchant_logos'),
        ),
    ]