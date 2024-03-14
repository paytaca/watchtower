# Generated by Django 3.0.14 on 2024-03-14 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0120_auto_20240314_0905'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservedName',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('key', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('redeemed_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
