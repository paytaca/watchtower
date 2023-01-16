# Generated by Django 3.0.14 on 2023-01-16 01:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('push_notifications', '0009_alter_apnsdevice_device_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceWallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wallet_hash', models.CharField(db_index=True, max_length=70)),
                ('last_active', models.DateTimeField()),
                ('apns_device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='device_wallets', to='push_notifications.APNSDevice')),
                ('gcm_device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='device_wallets', to='push_notifications.GCMDevice')),
            ],
        ),
    ]
