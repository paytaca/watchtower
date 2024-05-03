from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import logging
logger = logging.getLogger(__name__)

def send_order_update(data, order_id):
    room_name = f'ramp-p2p-subscribe-order-{order_id}'
    send_message(data, room_name)

def send_market_price(data, currency):
    room_name = f'ramp-p2p-subscribe-market-price-{currency.get("symbol")}'
    send_message(data, room_name)

def send_general_update(data, wallet_hash):
    room_name = f'ramp-p2p-subscribe-general-{wallet_hash}'
    send_message(data, room_name)

def send_message(data, room_name):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        room_name,
        {
            'type': 'send_message',
            'data': data
        }
    )