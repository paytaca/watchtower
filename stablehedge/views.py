from rest_framework import viewsets, mixins, decorators, exceptions
from rest_framework.response import Response
from django_filters import rest_framework as filters

from stablehedge import models
from stablehedge import serializers

from stablehedge.functions.treasury_contract import get_spendable_sats
from stablehedge.functions.anyhedge import (
    AnyhedgeException,
    get_short_contract_proposal,
    get_or_create_short_proposal,
    update_short_proposal_access_keys,
    update_short_proposal_funding_utxo_tx_sig,
)
from stablehedge.filters import (
    RedemptionContractFilter,
    RedemptionContractTransactionFilter,
)
from stablehedge.js.runner import ScriptFunctions


from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from stablehedge.functions.transaction import (
    test_transaction_accept,
    RedemptionContractTransactionException,
    create_inject_liquidity_tx,
    create_deposit_tx,
    create_redeem_tx,
)
from anyhedge import models as anyhedge_models
from main.tasks import NODE



class FiatTokenViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    lookup_field = "category"
    serializer_class = serializers.FiatTokenSerializer

    def get_queryset(self):
        return models.FiatToken.objects.all()


class RedemptionContractViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
):
    lookup_field = "address"
    serializer_class = serializers.RedemptionContractSerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RedemptionContractFilter

    def get_queryset(self):
        return models.RedemptionContract.objects \
            .annotate_redeemable() \
            .annotate_reserve_supply() \
            .select_related("treasury_contract") \
            .all()

    @decorators.action(
        methods=["get"], detail=False,
        serializer_class=serializers.serializers.Serializer,
    )
    def artifact(self, request, *args, **kwargs):
        result = ScriptFunctions.getRedemptionContractArtifact()

        # remove unnecessary data for compiling the contract
        result["artifact"].pop("source", None)
        # result["artifact"].pop("compiler", None)
        # result["artifact"].pop("updatedAt", None)

        return Response(result)

    @decorators.action(
        methods=["post"], detail=False,
        serializer_class=serializers.SweepRedemptionContractSerializer,
    )
    def sweep(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)

    @decorators.action(
        methods=["post"], detail=False,
        serializer_class=serializers.RedemptionContractTransactionSerializer,
    )
    def transaction(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(serializer.data)

class RedemptionContractTransactionViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
):
    serializer_class = serializers.RedemptionContractTransactionSerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RedemptionContractTransactionFilter

    def get_queryset(self):
        return models.RedemptionContractTransaction.objects.all()



class TreasuryContractViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
):
    lookup_field = "address"
    serializer_class = serializers.TreasuryContractSerializer

    def get_queryset(self):
        return models.TreasuryContract.objects \
            .select_related("redemption_contract") \
            .all()

    @decorators.action(
        methods=["get"], detail=False,
        serializer_class=serializers.serializers.Serializer,
    )
    def artifact(self, request, *args, **kwargs):
        result = ScriptFunctions.getTreasuryContractArtifact()

        # remove unnecessary data for compiling the contract
        result["artifact"].pop("source", None)
        # result["artifact"].pop("compiler", None)
        # result["artifact"].pop("updatedAt", None)

        return Response(result)

    @decorators.action(
        methods=["post"], detail=False,
        serializer_class=serializers.SweepTreasuryContractSerializer,
    )
    def sweep(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)

    @decorators.action(methods=["get"], detail=True)
    def balance(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(get_spendable_sats(instance.address))

    @decorators.action(methods=["get", "post"], detail=True)
    def short_proposal(self, request, *args, **kwargs):
        instance = self.get_object()
        if self.request.method == "GET": 
            result = get_short_contract_proposal(instance.address)
        elif self.request.method == "POST":
            result = get_or_create_short_proposal(instance.address)
        else:
            raise exceptions.MethodNotAllowed(self.request.method)

        return Response(result)

    @decorators.action(methods=["post"], detail=True)
    def short_proposal_access_keys(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            pubkey = request.data["pubkey"]
            signature = request.data["signature"]
            result = update_short_proposal_access_keys(instance.address, pubkey, signature)
            return Response(result)
        except AnyhedgeException as exception:
            result = {
                "detail": str(exception),
                "code": str(exception.code),
            }
            return Response(result, status=400)

    @decorators.action(methods=["post"], detail=True)
    def short_proposal_funding_utxo_tx_sig(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            sig = request.data["sig"]
            index = request.data["index"]
            result = update_short_proposal_funding_utxo_tx_sig(
                instance.address, sig,
                sig_index=index,
            )
            return Response(result)
        except AnyhedgeException as exception:
            result = {
                "detail": str(exception),
                "code": str(exception.code),
            }
            return Response(result, status=400)

class TestUtilsViewSet(viewsets.GenericViewSet):
    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter('price', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('wif', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Optional"),
            openapi.Parameter('save', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
        ],
    )
    @decorators.action(methods=["get"], detail=False)
    def price_message(self, request, *args, **kwargs):
        save = str(request.query_params.get("save", "")).lower().strip() == "true"
        wif = request.query_params.get("wif", None) or None
        try:
            price = int(request.query_params.get("price"))
        except (TypeError, ValueError):
            price = hash(request) % 2 ** 32 # almost random

        result = ScriptFunctions.generatePriceMessage(dict(price=price, wif=wif))

        if save:
            msg_timestamp = timezone.datetime.fromtimestamp(result["priceData"]["timestamp"] / 1000)
            msg_timestamp = timezone.make_aware(msg_timestamp)
            anyhedge_models.PriceOracleMessage.objects.update_or_create(
                pubkey=result["publicKey"],
                message=result["priceMessage"],
                defaults=dict(
                    signature=result["signature"],
                    message_timestamp=msg_timestamp,
                    price_value=result["priceData"]["price"],
                    price_sequence=result["priceData"]["dataSequence"],
                    message_sequence=result["priceData"]["msgSequence"],
                ),
            )

        result.pop("privateKey", None)
        return Response(result)

    @decorators.action(methods=["post"], detail=False, serializer_class=serializers.RedemptionContractTransactionSerializer)
    def test_redemption_contract_tx(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = { **serializer.validated_data}
        data["price_oracle_message"] = anyhedge_models.PriceOracleMessage(**data["price_oracle_message"])
        obj = models.RedemptionContractTransaction(**data)
        try:
            if obj.transaction_type == models.RedemptionContractTransaction.Type.INJECT:
                result = create_inject_liquidity_tx(obj)
            elif obj.transaction_type == models.RedemptionContractTransaction.Type.DEPOSIT:
                result = create_deposit_tx(obj)
            elif obj.transaction_type == models.RedemptionContractTransaction.Type.REDEEM:
                result = create_redeem_tx(obj)
            else:
                return Response(dict(success=False, error="Unknown type"))

            return Response(result)
        except RedemptionContractTransactionException as error:
            return Response(dict(success=False, error=str(error)))

    @decorators.action(methods=["post"], detail=False, serializer_class=serializers.serializers.Serializer)
    def test_mempool_accept(self, request, *args, **kwargs):
        success, error_or_txid = test_transaction_accept(request.data["transaction"])
        return Response(dict(success=success, result=error_or_txid))

    @decorators.action(methods=["post"], detail=False, serializer_class=serializers.serializers.Serializer)
    def decode_raw_tx(self, request, *args, **kwargs):
        result = NODE.BCH.build_tx_from_hex(request.data["transaction"])
        return Response(result)