# Generated by Django 3.0.14 on 2023-05-04 00:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0032_auto_20230502_0847'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='arbiter_address',
        ),
        migrations.RemoveField(
            model_name='order',
            name='buyer_address',
        ),
        migrations.RemoveField(
            model_name='order',
            name='contract_address',
        ),
        migrations.RemoveField(
            model_name='order',
            name='seller_address',
        ),
        migrations.AlterField(
            model_name='order',
            name='crypto_amount',
            field=models.FloatField(editable=False),
        ),
        migrations.AlterField(
            model_name='order',
            name='locked_price',
            field=models.FloatField(editable=False),
        ),
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('txid', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('contract_address', models.CharField(blank=True, max_length=100, null=True)),
                ('arbiter_address', models.CharField(blank=True, max_length=100, null=True)),
                ('buyer_address', models.CharField(blank=True, max_length=100, null=True)),
                ('seller_address', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='rampp2p.Order')),
            ],
        ),
    ]
