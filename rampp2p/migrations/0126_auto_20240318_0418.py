# Generated by Django 3.0.14 on 2024-03-18 04:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0125_auto_20240318_0404'),
    ]

    operations = [
        migrations.AddField(
            model_name='fiatcurrency',
            name='payment_types',
            field=models.ManyToManyField(to='rampp2p.PaymentType'),
        ),
        migrations.AlterField(
            model_name='fiatcurrency',
            name='symbol',
            field=models.CharField(db_index=True, max_length=3, unique=True),
        ),
    ]