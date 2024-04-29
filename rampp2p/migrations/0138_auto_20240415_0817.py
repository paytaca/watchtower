# Generated by Django 3.0.14 on 2024-04-15 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0137_update_chat_session_refs_20240405_0812'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='adsnapshot',
            name='payment_methods',
        ),
        migrations.AddField(
            model_name='adsnapshot',
            name='payment_types',
            field=models.ManyToManyField(related_name='ad_snapshots', to='rampp2p.PaymentType'),
        ),
    ]