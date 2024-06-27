from django.db.models.signals import post_save
from django.dispatch import receiver

from paytacapos.models import Merchant
from vouchers.vault import generate_merchant_vault

from slugify import slugify


@receiver(post_save, sender=Merchant)
def post_create_merchant(sender, instance=None, created=False, **kwargs):
    proceed = False
    if created:
        slug = slugify(instance.name)
        instance.slug = f'{slug}-{instance.id}'
        instance.save()

    if instance.receiving_pubkey:
        if created:
            proceed = True
        try:
            instance.vault
        except Merchant.vault.RelatedObjectDoesNotExist:
            proceed = True

    if proceed:
        generate_merchant_vault(instance.id)
