# Generated by Django 3.0.3 on 2020-08-05 11:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0038_auto_20200803_1059'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='spentIndex',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterUniqueTogether(
            name='transaction',
            unique_together={('txid', 'address', 'spentIndex')},
        ),
    ]
