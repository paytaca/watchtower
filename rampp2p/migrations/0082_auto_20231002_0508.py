# Generated by Django 3.0.14 on 2023-10-02 05:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0081_auto_20231002_0433'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='locked_price',
            field=models.DecimalField(decimal_places=8, default=0, editable=False, max_digits=18),
        ),
    ]