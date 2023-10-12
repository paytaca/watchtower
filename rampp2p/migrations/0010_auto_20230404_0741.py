# Generated by Django 3.0.14 on 2023-04-04 07:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0009_auto_20230404_0700'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='chat',
        ),
        migrations.AddField(
            model_name='chat',
            name='order',
            field=models.ForeignKey(default=1, editable=False, on_delete=django.db.models.deletion.SET_NULL, to='rampp2p.Order'),
            preserve_default=False,
        ),
    ]
