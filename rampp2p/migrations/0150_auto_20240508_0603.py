# Generated by Django 3.0.14 on 2024-05-08 06:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0149_auto_20240503_0644'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paymenttype',
            old_name='acc_name_req',
            new_name='acc_name_required',
        ),
        migrations.AddField(
            model_name='paymenttype',
            name='has_qr_code',
            field=models.BooleanField(default=False),
        ),
    ]