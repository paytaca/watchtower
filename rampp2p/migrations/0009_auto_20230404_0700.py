# Generated by Django 3.0.14 on 2023-04-04 07:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0008_chat_image_message_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='chat',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='rampp2p.Chat'),
        ),
    ]
