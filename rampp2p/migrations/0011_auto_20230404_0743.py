# Generated by Django 3.0.14 on 2023-04-04 07:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0010_auto_20230404_0741'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chat',
            name='order',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='rampp2p.Order'),
        ),
    ]
