from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import (
    F, Q, Value,
    OuterRef, Subquery,
    Func, Count,
    BigIntegerField,
)
from django.db.models.functions import Substr, Cast, Floor
from rest_framework import status
from main.models import Wallet, Address, WalletHistory
from django.core.paginator import Paginator
from main.serializers import PaginatedWalletHistorySerializer

POS_ID_MAX_DIGITS = 4

class WalletHistoryView(APIView):

    @swagger_auto_schema(
        responses={200: PaginatedWalletHistorySerializer},
        manual_parameters=[
            openapi.Parameter(name="page", type=openapi.TYPE_NUMBER, in_=openapi.IN_QUERY, default=1),
            openapi.Parameter(name="posid", type=openapi.TYPE_NUMBER, in_=openapi.IN_QUERY, required=False),
            openapi.Parameter(name="type", type=openapi.TYPE_STRING, in_=openapi.IN_QUERY, default="all", enum=["incoming", "outgoing"]),
        ]
    )
    def get(self, request, *args, **kwargs):
        wallet_hash = kwargs.get('wallethash', None)
        token_id = kwargs.get('tokenid', None)
        page = request.query_params.get('page', 1)
        record_type = request.query_params.get('type', 'all')
        posid = request.query_params.get("posid", None)

        qs = WalletHistory.objects.filter(wallet__wallet_hash=wallet_hash)
        if record_type in ['incoming', 'outgoing']:
            qs = qs.filter(record_type=record_type)

        if posid:
            try:
                posid = int(posid)
                posid = str(posid)
                pad = "0" * (POS_ID_MAX_DIGITS-len(posid))
                posid = pad + posid
            except (TypeError, ValueError):
                return Response(data=[f"invalid POS ID: {type(posid)}({posid})"], status=status.HTTP_400_BAD_REQUEST)

            addresses = Address.objects.filter(
                wallet_id=OuterRef("wallet_id"),
                address_path__iregex=f"((0|1)/)?0*\d+{posid}",
            ).values("address").distinct()
            addresses_subquery = Func(Subquery(addresses), function="array")
            qs = qs.filter(
                Q(senders__overlap=addresses_subquery) | Q(recipients__overlap=addresses_subquery),
            )

        wallet = Wallet.objects.get(wallet_hash=wallet_hash)
        qs = qs.order_by(F('tx_timestamp').desc(nulls_last=True), F('date_created').desc(nulls_last=True))
        
        if wallet.wallet_type == 'slp':
            qs = qs.filter(token__tokenid=token_id)
            history = qs.annotate(
                _token=F('token__tokenid')
            ).rename_annotations(
                _token='token_id'
            ).values(
                'record_type',
                'txid',
                'amount',
                'token',
                'tx_fee',
                'senders',
                'recipients',
                'date_created',
                'tx_timestamp',
                'usd_price',
                'market_prices',
            )
        elif wallet.wallet_type == 'bch':
            history = qs.values(
                'record_type',
                'txid',
                'amount',
                'tx_fee',
                'senders',
                'recipients',
                'date_created',
                'tx_timestamp',
                'usd_price',
                'market_prices',
            )
        if wallet.version == 1:
            return Response(data=history, status=status.HTTP_200_OK)
        else:
            pages = Paginator(history, 10)
            page_obj = pages.page(int(page))
            data = {
                'history': page_obj.object_list,
                'page': page,
                'num_pages': pages.num_pages,
                'has_next': page_obj.has_next()
            }
            return Response(data=data, status=status.HTTP_200_OK)


class LastAddressIndexView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(name="with_tx", type=openapi.TYPE_BOOLEAN, in_=openapi.IN_QUERY, default=False),
            openapi.Parameter(name="exclude_pos", type=openapi.TYPE_BOOLEAN, in_=openapi.IN_QUERY, default=False),
            openapi.Parameter(name="posid", type=openapi.TYPE_STRING, in_=openapi.IN_QUERY, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
            Get the last receiving address index of a wallet
        """
        wallet_hash = kwargs.get("wallethash", None)
        with_tx = request.query_params.get("with_tx", False)
        exclude_pos = request.query_params.get("exclude_pos", False)
        posid = request.query_params.get("posid", None)
        if posid is not None:
            try:
                posid = int(posid)
            except (TypeError, ValueError):
                return Response(data=[f"invalid POS ID: {type(posid)}({posid})"], status=status.HTTP_400_BAD_REQUEST)

        queryset = Address.objects.annotate(
            address_index = Cast(Substr(F("address_path"), Value("0/(\d+)")), BigIntegerField()),
        ).filter(
            wallet__wallet_hash=wallet_hash,
            address_index__isnull=False,
        )
        fields = ["address", "address_index"]
        ordering = ["-address_index"]

        if isinstance(with_tx, str) and with_tx.lower() == "false":
            with_tx = False

        if isinstance(exclude_pos, str) and exclude_pos.lower() == "false":
            exclude_pos = False

        if with_tx:
            queryset = queryset.annotate(tx_count = Count("transactions__txid", distinct=True))
            queryset = queryset.filter(tx_count__gt=0)
            ordering = ["-tx_count", "-address_index"]
            fields.append("tx_count")

        if isinstance(posid, int) and posid >= 0:
            POSID_MULTIPLIER = Value(10 ** POS_ID_MAX_DIGITS)
            queryset = queryset.annotate(posid=F("address_index") % POSID_MULTIPLIER)
            queryset = queryset.annotate(payment_index=Floor(F("address_index") / POSID_MULTIPLIER))
            queryset = queryset.filter(address_index__gte=POSID_MULTIPLIER)
            queryset = queryset.filter(posid=posid)
            # queryset = queryset.filter(address_index__gte=models.Value(0))
            fields.append("posid")
            fields.append("payment_index")
        elif exclude_pos:
            POSID_MULTIPLIER = Value(10 ** POS_ID_MAX_DIGITS)
            MAX_UNHARDENED_ADDRESS_INDEX = Value(2**32-1)
            queryset = queryset.exclude(
                address_index__gte=POSID_MULTIPLIER,
                address_index__lte=MAX_UNHARDENED_ADDRESS_INDEX,
            )

        queryset = queryset.values(*fields).order_by(*ordering)
        if len(queryset):
            address = queryset[0]
        else:
            address = None

        data = {
            "wallet_hash": wallet_hash,
            "address": address,
        }

        return Response(data)
