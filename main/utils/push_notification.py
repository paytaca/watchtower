from notifications.utils.send import send_push_notification_to_wallet_hashes, NotificationTypes
from django.conf import settings


def send_wallet_history_push_notification(wallet_history_obj):
    fiat_value = None
    decimals = 0
    if wallet_history_obj.cashtoken_ft:
        token = wallet_history_obj.cashtoken_ft
        token_name = settings.DEFAULT_TOKEN_DETAILS['fungible']['name']
        decimals = 0
        
        if token.info:
            token_name = token.info.symbol
            decimals = token.info.decimals
    else:
        token_name = wallet_history_obj.token.token_ticker or wallet_history_obj.token.name
        if token_name.lower() == "bch":
            token_name = "BCH"
        decimals = wallet_history_obj.token.decimals
        fiat_value = wallet_history_obj.fiat_value or wallet_history_obj.usd_value

    incoming = wallet_history_obj.amount >= 0
    extra = {
        "txid": wallet_history_obj.txid,
        "type": NotificationTypes.MAIN_TRANSACTION,
        "token_id": wallet_history_obj.token.tokenid,
    }

    if incoming:
        # title = "Payment Received" if incoming else "Payment Sent"
        title = "Payment Received"
        if token_name.lower() == "bch":
            amount = abs(wallet_history_obj.amount)
        else:
            amount = abs(wallet_history_obj.amount) / (10 ** decimals)
        amount = f'{amount:.5f}'.rstrip('0').rstrip('.')
        # message = f"{'Received' if incoming else 'Sent'} {amount} {token_name}"
        message = f"Received {amount} {token_name}"
        if fiat_value and fiat_value.get('value', None):
            message += f" ({abs(fiat_value['value'])} {fiat_value['currency']})"

        return send_push_notification_to_wallet_hashes(
            [wallet_history_obj.wallet.wallet_hash],
            message,
            title=title,
            extra=extra,   
        )
