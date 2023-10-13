# Generated by Django 3.0.14 on 2023-04-12 01:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0017_auto_20230411_0809'),
    ]

    operations = [
        migrations.CreateModel(
            name='Chat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('members', models.ManyToManyField(to='rampp2p.Peer')),
                ('order', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='rampp2p.Order')),
            ],
        ),
        migrations.AlterField(
            model_name='feedback',
            name='from_peer',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='created_feedbacks', to='rampp2p.Peer'),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='to_peer',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='received_feedbacks', to='rampp2p.Peer'),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(editable=False, max_length=4000)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('chat', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='rampp2p.Chat')),
                ('from_peer', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='rampp2p.Peer')),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(editable=False, max_length=100)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='rampp2p.Message')),
            ],
        ),
    ]
