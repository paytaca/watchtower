# Generated by Django 3.0.14 on 2024-07-18 06:46

from django.db import migrations
import logging
logger = logging.getLogger(__name__)

# create fields for each paymenttype
def init_paymenttype_fields(apps, schema_editor):
    PaymentType = apps.get_model('rampp2p', 'PaymentType')
    PaymentTypeField = apps.get_model('rampp2p', 'PaymentTypeField')
    payment_types = PaymentType.objects.all()
    for payment_type in payment_types:
        logger.warn(f'Creating fields for payment type: {payment_type.full_name}')

        fieldnamedata = {
            'fieldname': 'Account Name',
            'format': '^(?=.*[a-zA-Z])(?=.*[0-9])[A-Za-z0-9 .]+$',
            'payment_type': payment_type,
            'required': payment_type.acc_name_required
        }
        PaymentTypeField.objects.create(**fieldnamedata)
        formats = payment_type.formats.all()
        logger.warn(f'{formats.count()} formats for {payment_type.full_name}')
        for format in formats:
            fielddata = {
                'fieldname': format.format,
                'payment_type': payment_type,
                'required': False
            }
            PaymentTypeField.objects.create(**fielddata)

class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0167_paymentmethodfield_paymenttypefield'),
    ]

    operations = [
        migrations.RunPython(init_paymenttype_fields)
    ]

