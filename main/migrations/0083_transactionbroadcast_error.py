# Generated by Django 3.0.14 on 2024-01-26 18:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0082_auto_20240126_1758'),
    ]

    operations = [
        migrations.AddField(
            model_name='transactionbroadcast',
            name='error',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
