# Generated by Django 3.0.14 on 2024-11-22 03:03

from django.db import migrations
from rampp2p.utils import fiat_to_bch, bch_to_satoshi
from rampp2p.models import PriceType

import logging
logger = logging.getLogger(__name__)

def get_price(ad):
    if ad.price_type == PriceType.FIXED:
        return ad.fixed_price
    return ad.market_price * (ad.floating_price/100)

def init_ad_snapshot_trade_limit_sats(apps, schema_editor):
    AdSnapshot = apps.get_model('rampp2p', 'AdSnapshot')
    ads = AdSnapshot.objects.all()

    for ad in ads:
        price = get_price(ad)
        if price == None:
            continue
        
        trade_amount = ad.trade_amount
        if ad.trade_amount_in_fiat:
            # convert fiat to bch
            trade_amount = fiat_to_bch(trade_amount, price)
        # convert bch to satoshi
        ad.trade_amount_sats = bch_to_satoshi(trade_amount)

        trade_floor = ad.trade_floor
        trade_ceiling = ad.trade_ceiling
        if ad.trade_limits_in_fiat:
            # convert fiat to bch
            trade_floor = fiat_to_bch(trade_floor, price)
            trade_ceiling = fiat_to_bch(trade_ceiling, price)
        # convert bch to satoshi
        ad.trade_floor_sats = bch_to_satoshi(trade_floor)
        ad.trade_ceiling_sats = bch_to_satoshi(trade_ceiling)
        ad.save()

        logger.info(f'AdSnapshot#{ad.id} | trade_amount_sats: {ad.trade_amount_sats} | trade_floor_sats: {ad.trade_floor_sats} | trade_ceiling_sats: {ad.trade_ceiling_sats}')

class Migration(migrations.Migration):

    dependencies = [
        ('rampp2p', '0209_auto_20241122_0303'),
    ]

    operations = [
        migrations.RunPython(init_ad_snapshot_trade_limit_sats)
    ]

