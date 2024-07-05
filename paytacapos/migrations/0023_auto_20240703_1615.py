# Generated by Django 3.0.14 on 2024-07-03 16:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paytacapos', '0022_merchant_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='province',
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
        migrations.AddField(
            model_name='location',
            name='state',
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
        migrations.AddField(
            model_name='location',
            name='town',
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
    ]