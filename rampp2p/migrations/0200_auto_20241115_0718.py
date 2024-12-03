# Generated by Django 3.0.14 on 2024-11-15 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0199_auto_20241114_0955'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='amount',
            field=models.IntegerField(editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='crypto_amount',
            field=models.DecimalField(decimal_places=8, default=0, editable=False, max_digits=18, null=True),
        ),
    ]
