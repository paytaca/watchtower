# Generated by Django 3.0.14 on 2023-05-25 03:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0040_auto_20230522_0634'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipient',
            name='amount',
            field=models.DecimalField(decimal_places=8, default=0, editable=False, max_digits=10),
        ),
    ]