# Generated by Django 3.0.14 on 2024-11-15 07:28

from django.db import migrations
from django.conf import settings
from django.db.models import Q

import logging
logger = logging.getLogger(__name__)

def init_empty_contract_fees(apps, schema_editor):
    Contract = apps.get_model('rampp2p', 'Contract')
    contracts = Contract.objects.filter(Q(contract_fee__isnull=True) | Q(arbitration_fee__isnull=True) | Q(service_fee__isnull=True))
    logger.info(f'Found {contracts.count()} contracts')

    for contract in contracts:
        logger.info(f'Initializing Contract #{contract.id} | contract_fee: {settings.CONTRACT_FEE} | arbitration_fee: {settings.ARBITRATION_FEE} | service_fee: {settings.SERVICE_FEE}')
        contract.contract_fee = int(settings.CONTRACT_FEE)
        contract.arbitration_fee = int(settings.ARBITRATION_FEE)
        contract.service_fee = int(settings.SERVICE_FEE)
        contract.save()

class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0201_auto_20241115_0720'),
    ]

    operations = [
        migrations.RunPython(init_empty_contract_fees)
    ]

