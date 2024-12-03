# Generated by Django 3.0.14 on 2024-11-26 09:50

from django.db import migrations

import logging
logger = logging.getLogger(__name__)

def min_required_version_0_20_2(apps, schema_editor):
    AppVersion = apps.get_model('main', 'AppVersion')
    latest_version = '0.20.2'
    min_required_version = '0.20.2'
    platforms = ['ios', 'android', 'web']
    for platform in platforms:
        version, created = AppVersion.objects.get_or_create(
            platform=platform, 
            latest_version=latest_version, 
            min_required_version=min_required_version)
        
        logger.warning(f'Created={created} AppVersion platform={version.platform} latest={version.latest_version} min={version.min_required_version}')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0093_auto_20241125_0722'),
    ]

    operations = [
        migrations.RunPython(min_required_version_0_20_2)
    ]
