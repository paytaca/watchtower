import pytz
from datetime import datetime, timedelta
from django.db import transaction
from rest_framework import serializers

from .conf import settings as app_settings
from .models import (
    LongAccount,
    HedgePosition,
    HedgeSettlement,
    SettlementService,
    HedgePositionFee,
    HedgeFundingProposal,
    MutualRedemption,
    HedgePositionOffer,
    HedgePositionFunding,

    Oracle,
    PriceOracleMessage,
)
from .utils.address import match_pubkey_to_cash_address
from .utils.contract import (
    create_contract,
    get_contract_status
)
from .utils.funding import (
    get_tx_hash,
    validate_funding_transaction,
)
from .utils.liquidity import (
    consume_long_account_allowance,
    get_position_offer_suggestions,
    fund_hedge_position,
)
from .utils.validators import (
    ValidAddress,
    ValidTxHash,
)
from .utils.websocket import (
    send_offer_settlement_update,
    send_funding_tx_update,
    send_mutual_redemption_update,
)
from .tasks import validate_contract_funding


class TimestampField(serializers.IntegerField):
    def to_representation(self, value):
        return datetime.timestamp(value)

    def to_internal_value(self, data):
        return datetime.fromtimestamp(data).replace(tzinfo=pytz.UTC)


class FundingProposalSerializer(serializers.Serializer):
    hedge_address = serializers.CharField(validators=[ValidAddress(addr_type=ValidAddress.TYPE_CASHADDR)])
    position = serializers.CharField() # hedge | long
    tx_hash = serializers.CharField(validators=[ValidTxHash()])
    tx_index = serializers.IntegerField()
    tx_value = serializers.IntegerField()
    script_sig = serializers.CharField()
    pubkey = serializers.CharField(required=False)
    input_tx_hashes = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    def validate_hedge_address(self, value):
        try:
            hedge_position_obj = HedgePosition.objects.get(address=value)
            if hedge_position_obj.funding_tx_hash:
                raise serializers.ValidationError("Hedge position is already funded")
            try:
                if hedge_position_obj.settlement:
                    raise serializers.ValidationError("Hedge position is already settled")
            except HedgePosition.settlement.RelatedObjectDoesNotExist:
                pass

        except HedgePosition.DoesNotExist:
            raise serializers.ValidationError("Hedge position does not exist")

        return value

    def validate_position(self, value):
        if value != "hedge" and value != "long":
            raise serializers.ValidationError("Position must be \"hedge\" or \"long\"")
        return value

    @transaction.atomic()
    def create(self, validated_data):
        hedge_address = validated_data.pop("hedge_address")
        position = validated_data.pop("position")
        hedge_pos_obj = HedgePosition.objects.get(address=hedge_address)

        update_hedge_obj = True

        funding_proposal = HedgeFundingProposal()
        if position == "hedge" and hedge_pos_obj.hedge_funding_proposal:
            funding_proposal = hedge_pos_obj.hedge_funding_proposal
            update_hedge_obj = False
        elif position == "long" and hedge_pos_obj.long_funding_proposal:
            funding_proposal = hedge_pos_obj.long_funding_proposal
            update_hedge_obj = False

        funding_proposal.tx_hash = validated_data["tx_hash"]
        funding_proposal.tx_index = validated_data["tx_index"]
        funding_proposal.tx_value = validated_data["tx_value"]
        funding_proposal.script_sig = validated_data["script_sig"]
        funding_proposal.pubkey = validated_data["pubkey"]
        funding_proposal.input_tx_hashes = validated_data.get("input_tx_hashes", None)
        funding_proposal.save()

        if update_hedge_obj:
            if position == "hedge":
                hedge_pos_obj.hedge_funding_proposal = funding_proposal
            elif position == "long":
                hedge_pos_obj.long_funding_proposal = funding_proposal
            hedge_pos_obj.save()

        send_funding_tx_update(hedge_pos_obj, position=position)
        return funding_proposal


class LongAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LongAccount
        fields = [
            "id",
            "wallet_hash",
            "address_path",
            "address",
            "pubkey",

            "min_auto_accept_duration",
            "max_auto_accept_duration",
            "auto_accept_allowance",
        ]

    def validate(self, data):
        if "pubkey" in data and "address" in data or not self.instance:
            if not match_pubkey_to_cash_address(data["pubkey"], data["address"]):
                raise serializers.ValidationError("public key & address does not match")
        return data


class HedgeFundingProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HedgeFundingProposal
        fields = [
            "tx_hash",
            "tx_index",
            "tx_value",
            "script_sig",
            "pubkey",
            "input_tx_hashes",
        ]


class HedgeSettlementSerializer(serializers.ModelSerializer):
    settlement_message_timestamp = TimestampField()

    class Meta:
        model = HedgeSettlement
        fields = [
            "spending_transaction",
            "settlement_type",
            "hedge_satoshis",
            "long_satoshis",
            "oracle_pubkey",
            "settlement_price",
            "settlement_price_sequence",
            "settlement_message_sequence",
            "settlement_message_timestamp",
        ]


class SettlementServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementService
        fields = [
            "domain",
            "scheme",
            "port",
            "hedge_signature",
            "long_signature",
        ]

    def validate(self, data):
        if not data.get("hedge_signature", None) and not data.get("long_signature", None):
            raise serializers.ValidationError("hedge_signature or long_signature must be given")
        return data


class HedgePositionFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HedgePositionFee
        fields = [
            "address",
            "satoshis",
        ]

class HedgePositionFundingSerializer(serializers.ModelSerializer):
    class Meta:
        model = HedgePositionFunding
        fields = [
            "tx_hash",
            "funding_output",
            "funding_satoshis",
            "fee_output",
            "fee_satoshis",
        ]


class MutualRedemptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = MutualRedemption
        fields = [
            "redemption_type",
            "hedge_satoshis",
            "long_satoshis",
            "hedge_schnorr_sig",
            "long_schnorr_sig",
            "settlement_price",
            "tx_hash",
        ]

        extra_kwargs = {
            "tx_hash": {
                "read_only": True,
            },
        }

    def __init__(self, *args, hedge_position=None, **kwargs):
        self.hedge_position = hedge_position
        return super().__init__(*args, **kwargs)

    def validate_redemption_type(self, value):
        if self.instance and self.instance.redemption_type != value:
            raise serializers.ValidationError("Redemption type is not editable")
        return value

    def validate_hedge_satoshis(self, value):
        if self.instance and self.instance.hedge_satoshis != value:
            raise serializers.ValidationError("Hedge satoshis is not editable")
        return value

    def validate_long_satoshis(self, value):
        if self.instance and self.instance.long_satoshis != value:
            raise serializers.ValidationError("Long satoshis is not editable")
        return value

    def validate_settlement_price(self, value):
        if self.instance and self.instance.settlement_price != value:
            raise serializers.ValidationError("Settlement price is not editable")
        return value

    def validate(self, data):
        redemption_type = data.get("redemption_type", None)
        settlement_price = data.get("settlement_price", None)
        hedge_satoshis = data.get("hedge_satoshis", None)
        long_satoshis = data.get("long_satoshis", None)

        if not self.hedge_position.funding_tx_hash:
            raise serializers.ValidationError("Contract is not yet funded")

        if not self.hedge_position.funding:
            funding_validation = validate_contract_funding(self.hedge_position.address)
            if not funding_validation["success"] or not self.hedge_position.funding:
                raise serializers.ValidationError("Unable to verify funding transaction")

        if redemption_type == MutualRedemption.TYPE_EARLY_MATURATION:
            if not settlement_price and settlement_price <= 0:
                raise serializers.ValidationError(f"Settlement price required for type '{MutualRedemption.TYPE_EARLY_MATURATION}'")

        elif redemption_type == MutualRedemption.TYPE_REFUND:
            if abs(hedge_satoshis - self.hedge_position.satoshis) > 1:
                raise serializers.ValidationError(f"Hedge payout must be {self.hedge_position.satoshis} for type '{MutualRedemption.TYPE_REFUND}'")
            elif abs(long_satoshis - self.hedge_position.long_input_sats) > 1:
                raise serializers.ValidationError(f"Long payout must be {self.hedge_position.long_input_sats} for type '{MutualRedemption.TYPE_REFUND}'")

        # calculations from anyhedge library leaves 1175 for tx fee
        tx_fee = 1175
        expected_total_output = self.hedge_position.funding.funding_satoshis - tx_fee
        total_output = hedge_satoshis + long_satoshis
        if expected_total_output != total_output:
            raise serializers.ValidationError(f"Payout satoshis is not equal to {expected_total_output}")

        return data

    def create(self, validated_data):
        instance = MutualRedemption.objects.filter(hedge_position=self.hedge_position).first()

        if not instance:
            instance = MutualRedemption(hedge_position=self.hedge_position, **validated_data)

        if instance.long_satoshis != validated_data["long_satoshis"] or \
            instance.hedge_satoshis != validated_data["hedge_satoshis"] or \
            instance.redemption_type != validated_data["redemption_type"]:

            instance.hedge_schnorr_sig = None
            instance.long_schnorr_sig = None

        instance.long_satoshis = validated_data["long_satoshis"]
        instance.hedge_satoshis = validated_data["hedge_satoshis"]
        instance.redemption_type = validated_data["redemption_type"]
        instance.settlement_price = validated_data.get("settlement_price", None)

        if validated_data.get("hedge_schnorr_sig", None):
            instance.hedge_schnorr_sig = validated_data["hedge_schnorr_sig"]

        if validated_data.get("long_schnorr_sig", None):
            instance.long_schnorr_sig = validated_data["long_schnorr_sig"]

        instance.save()
        send_mutual_redemption_update(instance, action="created")
        return instance


class HedgePositionSerializer(serializers.ModelSerializer):
    hedge_funding_proposal = HedgeFundingProposalSerializer(required=False)
    long_funding_proposal = HedgeFundingProposalSerializer(required=False)
    start_timestamp = TimestampField()
    maturity_timestamp = TimestampField()

    settlement = HedgeSettlementSerializer(read_only=True)
    settlement_service = SettlementServiceSerializer()
    check_settlement_service = serializers.BooleanField(default=True, required=False, write_only=True)
    fee = HedgePositionFeeSerializer()
    funding = HedgePositionFundingSerializer(read_only=True)
    mutual_redemption = MutualRedemptionSerializer(read_only=True)

    class Meta:
        model = HedgePosition
        fields = [
            "id",
            "address",
            "anyhedge_contract_version",
            "satoshis",
            "start_timestamp",
            "maturity_timestamp",
            "hedge_wallet_hash",
            "hedge_address",
            "hedge_pubkey",
            "hedge_address_path",
            "long_wallet_hash",
            "long_address",
            "long_pubkey",
            "long_address_path",
            "oracle_pubkey",
            "start_price",
            "low_liquidation_multiplier",
            "high_liquidation_multiplier",
            "funding_tx_hash",
            "funding_tx_hash_validated",
            "hedge_funding_proposal",
            "long_funding_proposal",

            "settlement",
            "settlement_service",
            "check_settlement_service",
            "fee",
            "funding",
            "mutual_redemption",
        ]
        extra_kwargs = {
            "address": {
                "validators": [ValidAddress(addr_type=ValidAddress.TYPE_CASHADDR)]
            },
            "hedge_address": {
                "validators": [ValidAddress(addr_type=ValidAddress.TYPE_CASHADDR)]
            },
            "long_address": {
                "validators": [ValidAddress(addr_type=ValidAddress.TYPE_CASHADDR)]
            },
            "hedge_wallet_hash": {
                "allow_blank": True
            },
            "long_wallet_hash": {
                "allow_blank": True
            },
            "funding_tx_hash": {
                "allow_blank": True
            },
            "funding_tx_hash_validated": {
                "read_only": True
            },
        }

    def validate(self, data):
        contract_address = data.get("address", None)
        oracle_pubkey = data.get("oracle_pubkey", None)
        settlement_service = data.get("settlement_service", None)
        check_settlement_service = data.get("check_settlement_service", None)
        hedge_pubkey = data.get("hedge_pubkey", None)
        long_pubkey = data.get("long_pubkey")

        if not match_pubkey_to_cash_address(data["hedge_pubkey"], data["hedge_address"]):
            raise serializers.ValidationError("hedge public key & address does not match")

        if not match_pubkey_to_cash_address(data["long_pubkey"], data["long_address"]):
            raise serializers.ValidationError("long public key & address does not match")

        if settlement_service and check_settlement_service:
            access_pubkey = ""
            access_signature = ""
            if settlement_service.get("hedge_signature", None):
                access_signature = settlement_service["hedge_signature"]
                access_pubkey = hedge_pubkey
            elif settlement_service.get("long_signature", None):
                access_signature = settlement_service["long_signature"]
                access_pubkey = long_pubkey
            contract_data = get_contract_status(
                contract_address,
                access_pubkey,
                access_signature,
                settlement_service_scheme=settlement_service["scheme"],
                settlement_service_domain=settlement_service["domain"],
                settlement_service_port=settlement_service["port"],
            )
            if not contract_data or contract_data.get("address", None) != contract_address:
                raise serializers.ValidationError("Unable to verify contract from external settlement service")
        elif not settlement_service:
            if not Oracle.objects.filter(pubkey=oracle_pubkey).exists():
                raise serializers.ValidationError("Unknown 'oracle_pubkey', must provide settlement service")

        return data

    @transaction.atomic()
    def create(self, validated_data):
        validated_data.pop("check_settlement_service", None)
        settlement_service_data = validated_data.pop("settlement_service", None)
        fee_data = validated_data.pop("fee", None)
        hedge_funding_proposal_data = validated_data.pop("hedge_funding_proposal", None)
        long_funding_proposal_data = validated_data.pop("long_funding_proposal", None)

        instance = super().create(validated_data)
        save_instance = False

        if settlement_service_data is not None:
            settlement_service_data["hedge_position"] = instance
            SettlementService.objects.create(**settlement_service_data)
        
        if fee_data is not None:
            fee_data["hedge_position"] = instance
            HedgePositionFee.objects.create(**fee_data)

        if hedge_funding_proposal_data is not None:
            hedge_funding_proposal = HedgeFundingProposal.objects.create(**hedge_funding_proposal_data)
            instance.hedge_funding_proposal = hedge_funding_proposal
            save_instance = True

        if long_funding_proposal_data is not None:
            long_funding_proposal = HedgeFundingProposal.objects.create(**long_funding_proposal_data)
            instance.long_funding_proposal = long_funding_proposal
            save_instance = True

        if save_instance:
            instance.save()

        return instance


class HedgePositionOfferSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    hedge_position = HedgePositionSerializer(read_only=True)
    auto_settled = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    auto_match = serializers.BooleanField(default=False, write_only=True)

    price_oracle_message_sequence = serializers.IntegerField(required=False, write_only=True)

    # Create a hedge position without saving the hedge position offer by setting this to false and;
    # setting auto_match to true
    save_position_offer = serializers.BooleanField(default=True, write_only=True)

    class Meta:
        model = HedgePositionOffer
        fields = [
            "id",
            "status",
            "wallet_hash",
            "satoshis",
            "duration_seconds",
            "high_liquidation_multiplier",
            "low_liquidation_multiplier",
            "oracle_pubkey",
            "hedge_address",
            "hedge_pubkey",
            "hedge_address_path",
            "hedge_position",
            "auto_settled",
            "created_at",
            "auto_match",
            "price_oracle_message_sequence",
            "save_position_offer",
        ]

    def validate(self, data):
        save_position_offer = data.get("save_position_offer", None)
        auto_match = data.get("auto_match", None)
        if not match_pubkey_to_cash_address(data["hedge_pubkey"], data["hedge_address"]):
            raise serializers.ValidationError("public key & address does not match")

        if not auto_match and not save_position_offer:
            raise serializers.ValidationError("'save_position_offer' or 'auto_match' must either be selected")

        return data

    @transaction.atomic()
    def create(self, validated_data, *args, **kwargs):
        auto_match = validated_data.pop("auto_match", False)
        price_oracle_message_sequence = validated_data.pop("price_oracle_message_sequence", None)
        save_position_offer = validated_data.pop("save_position_offer", None)

        instance = self.init_instance(validated_data, save=save_position_offer)

        if auto_match:
            instance = self.auto_match_p2p(instance, price_oracle_message_sequence=price_oracle_message_sequence)
        return instance

    def init_instance(self, validated_data, save=False):
        if save:
            instance = super().create(validated_data)
        else:
            instance = self.Meta.model(**validated_data)

        return instance

    @classmethod
    def auto_match_p2p(cls, instance:HedgePositionOffer, price_oracle_message_sequence=None) -> HedgePositionOffer:
        long_accounts = get_position_offer_suggestions(
            amount=instance.satoshis,
            duration_seconds=instance.duration_seconds,
            low_liquidation_multiplier=instance.low_liquidation_multiplier,
            high_liquidation_multiplier=instance.high_liquidation_multiplier,
            exclude_wallet_hash=instance.wallet_hash,
        )
        if long_accounts:
            long_account = long_accounts[0]
            response = create_contract(
                satoshis=instance.satoshis,
                low_price_multiplier=instance.low_liquidation_multiplier,
                high_price_multiplier=instance.high_liquidation_multiplier,
                duration_seconds=instance.duration_seconds,
                hedge_address=instance.hedge_address,
                hedge_pubkey=instance.hedge_pubkey,
                short_address=long_account.address,
                short_pubkey=long_account.pubkey,
                oracle_pubkey=instance.oracle_pubkey,
                price_oracle_message_sequence=price_oracle_message_sequence,
            )

            if "success" in response and response["success"]:
                contract_data = response["contractData"]
                settle_hedge_position_offer_data = {
                    "address": contract_data["address"],
                    "anyhedge_contract_version": contract_data["version"],
                    "oracle_pubkey": contract_data["metadata"]["oraclePublicKey"],
                    "oracle_price": contract_data["metadata"]["startPrice"],
                    "oracle_timestamp": contract_data["metadata"]["startTimestamp"],
                    "long_wallet_hash": long_account.wallet_hash,
                    "long_address": contract_data["metadata"]["longAddress"],
                    "long_pubkey": contract_data["metadata"]["longPublicKey"],
                    "long_address_path": long_account.address_path,
                }

                settle_hedge_position_offer_serializer = SettleHedgePositionOfferSerializer(
                    data=settle_hedge_position_offer_data,
                    hedge_position_offer=instance,
                    auto_settled=True,
                )
                settle_hedge_position_offer_serializer.is_valid(raise_exception=True)
                instance = settle_hedge_position_offer_serializer.save()
            else:
                error = "Error creating contract data"
                script_error = response.get("error", None)
                if script_error:
                    error += f". {script_error}"
                raise Exception(error)
        else:
            raise Exception(f"Failed to find match for {instance}")
        return instance

class SettleHedgePositionOfferSerializer(serializers.Serializer):
    address = serializers.CharField(validators=[ValidAddress(addr_type=ValidAddress.TYPE_CASHADDR)])
    anyhedge_contract_version = serializers.CharField()
    oracle_pubkey = serializers.CharField()
    oracle_price = serializers.IntegerField()
    oracle_timestamp = serializers.IntegerField() # unix
    long_wallet_hash = serializers.CharField(allow_blank=True)
    long_address = serializers.CharField(validators=[ValidAddress(addr_type=ValidAddress.TYPE_CASHADDR)])
    long_pubkey = serializers.CharField()
    long_address_path = serializers.CharField(required=False)

    def __init__(self, *args, hedge_position_offer=None, auto_settled=False, **kwargs):
        self.hedge_position_offer = hedge_position_offer
        self.auto_settled = auto_settled
        return super().__init__(*args, **kwargs)

    def validate(self, data):
        assert isinstance(self.hedge_position_offer, HedgePositionOffer), \
            f"Expected type {HedgePositionOffer} but got {type(self.hedge_position_offer)}"

        if self.hedge_position_offer.status == HedgePositionOffer.STATUS_SETTLED:
            raise serializers.ValidationError("Hedge position offer is already settled")
        elif self.hedge_position_offer.status == HedgePositionOffer.STATUS_CANCELLED:
            raise serializers.ValidationError("Hedge position offer is already cancelled")
        elif self.hedge_position_offer.hedge_position:
            self.hedge_position_offer.status = HedgePositionOffer.STATUS_SETTLED
            self.hedge_position_offer.save()
            raise serializers.ValidationError("Hedge position offer is already settled")

        if not match_pubkey_to_cash_address(data["long_pubkey"], data["long_address"]):
            raise serializers.ValidationError("public key & address does not match")

        return data

    @transaction.atomic()
    def save(self):
        validated_data = self.validated_data
        start_timestamp = datetime.fromtimestamp(validated_data["oracle_timestamp"]).replace(tzinfo=pytz.UTC)
        maturity_timestamp = start_timestamp + timedelta(seconds=self.hedge_position_offer.duration_seconds) 

        hedge_position = HedgePosition.objects.create(
            address = validated_data["address"],
            anyhedge_contract_version = validated_data["anyhedge_contract_version"],
            satoshis = self.hedge_position_offer.satoshis,
            start_timestamp = start_timestamp,
            maturity_timestamp = maturity_timestamp,
            hedge_wallet_hash = self.hedge_position_offer.wallet_hash,
            hedge_address = self.hedge_position_offer.hedge_address,
            hedge_pubkey = self.hedge_position_offer.hedge_pubkey,
            hedge_address_path = self.hedge_position_offer.hedge_address_path,
            long_wallet_hash = validated_data["long_wallet_hash"],
            long_address = validated_data["long_address"],
            long_pubkey = validated_data["long_pubkey"],
            long_address_path = validated_data.get("long_address_path", None),
            oracle_pubkey = validated_data["oracle_pubkey"],
            start_price = validated_data["oracle_price"],
            low_liquidation_multiplier = self.hedge_position_offer.low_liquidation_multiplier,
            high_liquidation_multiplier = self.hedge_position_offer.high_liquidation_multiplier,
        )

        self.hedge_position_offer.hedge_position = hedge_position
        self.hedge_position_offer.status = HedgePositionOffer.STATUS_SETTLED
        self.hedge_position_offer.auto_settled = self.auto_settled
        if self.hedge_position_offer.id:
            self.hedge_position_offer.save()

        if self.auto_settled:
            consume_long_account_allowance(hedge_position.long_address, hedge_position.long_input_sats)

        send_offer_settlement_update(self.hedge_position_offer)
        return self.hedge_position_offer


class SubmitFundingTransactionSerializer(serializers.Serializer):
    hedge_position_address = serializers.CharField(validators=[ValidAddress(addr_type=ValidAddress.TYPE_CASHADDR)])
    tx_hash = serializers.CharField(validators=[ValidTxHash()], required=False)
    tx_hex = serializers.CharField(required=False)

    def validate_hedge_address(value):
        try:
            hedge_position_obj = HedgePosition.objects.get(address=value)
        except HedgePosition.DoesNotExist:
            raise serializers.ValidationError("Hedge position does not exist")

        return value

    def validate(self, data):
        hedge_position_address = data.get("hedge_position_address", None)
        tx_hash = data.get("tx_hash", None)
        tx_hex = data.get("tx_hex", None)
        if not tx_hash and not tx_hex:
            raise serializers.ValidationError("tx_hash or tx_hex required")

        # TODO: route for broadcasting tx_hex if necessary
        if tx_hash:
            funding_tx_validation = validate_funding_transaction(tx_hash, hedge_position_address)
            if not funding_tx_validation["valid"]:
                raise serializers.ValidationError(f"funding tx hash '{tx_hash}' invalid")
        elif tx_hex:
            _tx_hash = get_tx_hash(tx_hex)
            funding_tx_validation = validate_funding_transaction(_tx_hash, hedge_position_address)
            if not funding_tx_validation["valid"]:
                raise serializers.ValidationError(f"funding tx hex invalid")

        return data
    
    @transaction.atomic()
    def save(self):
        validated_data = self.validated_data
        hedge_position_address = validated_data["hedge_position_address"]

        tx_hash = validated_data.get("tx_hash", None)
        if not tx_hash:
            tx_hash = get_tx_hash(validated_data["tx_hex"])

        hedge_position_obj = HedgePosition.objects.get(address=hedge_position_address)

        if hedge_position_obj.funding_tx_hash != tx_hash:
            hedge_position_obj.funding_tx_hash_validated = False

        hedge_position_obj.funding_tx_hash = tx_hash
        hedge_position_obj.save()
        send_funding_tx_update(hedge_position_obj, tx_hash=hedge_position_obj.funding_tx_hash)
        return hedge_position_obj


class FundGeneralProcotolLPContractSerializer(serializers.Serializer):
    contract_address = serializers.CharField()
    position = serializers.ChoiceField(choices=["hedge", "long"])
    hedge_wallet_hash = serializers.CharField(required=False)
    hedge_pubkey = serializers.CharField(required=False)
    hedge_address_path = serializers.CharField(required=False)

    long_wallet_hash = serializers.CharField(required=False)
    long_pubkey = serializers.CharField(required=False)
    long_address_path = serializers.CharField(required=False)
    oracle_message_sequence = serializers.IntegerField()

    settlement_service = SettlementServiceSerializer() # do i need this here or js script will provide ?
    funding_proposal = HedgeFundingProposalSerializer()

    def validate(self, data):
        position = data["position"]
        hedge_wallet_hash = data.get("hedge_wallet_hash", None)
        hedge_pubkey = data.get("hedge_pubkey", None)
        long_wallet_hash = data.get("long_wallet_hash", None)
        long_pubkey = data.get("long_pubkey", None)

        if position == "hedge" and (not hedge_wallet_hash or not hedge_pubkey):
            raise serializers.ValidationError("'hedge_wallet_hash' or 'hedge_pubkey' required when taking 'hedge' position")

        if position == "long" and (not long_wallet_hash or not long_pubkey):
            raise serializers.ValidationError("'long_wallet_hash' or 'long_pubkey' required when taking 'long' position")

        return data

    @transaction.atomic()
    def save(self):
        validated_data = self.validated_data
        contract_address = validated_data["contract_address"]
        position = validated_data["position"]
        hedge_wallet_hash = validated_data.get("hedge_wallet_hash", None)
        hedge_pubkey = validated_data.get("hedge_pubkey", None)
        hedge_address_path = validated_data.get("hedge_address_path", None)
        long_wallet_hash = validated_data.get("long_wallet_hash", None)
        long_pubkey = validated_data.get("long_pubkey", None)
        long_address_path = validated_data.get("long_address_path", None)

        oracle_message_sequence = validated_data["oracle_message_sequence"]
        settlement_service = validated_data["settlement_service"]
        funding_proposal = validated_data["funding_proposal"]

        access_pubkey = ""
        access_signature = ""
        if settlement_service.get("hedge_signature", None):
            access_signature = settlement_service["hedge_signature"]
            access_pubkey = hedge_pubkey
        elif settlement_service.get("long_signature", None):
            access_signature = settlement_service["long_signature"]
            access_pubkey = long_pubkey

        contract_data = get_contract_status(
            contract_address,
            access_pubkey,
            access_signature,
            settlement_service_scheme=settlement_service["scheme"],
            settlement_service_domain=settlement_service["domain"],
            settlement_service_port=settlement_service["port"],
        )

        if contract_data["address"] != contract_address:
            raise serializers.ValidationError("Contract address from settlement does not match")

        contract_metadata = contract_data["metadata"]
        start_timestamp = contract_metadata["startTimestamp"]
        maturity_timestamp = start_timestamp + contract_metadata["duration"]

        hedge_position_data = {
            "address": contract_data["address"],
            "anyhedge_contract_version": contract_data["version"],
            "satoshis": contract_metadata["hedgeInputSats"],
            "start_timestamp": contract_metadata["startTimestamp"],
            "maturity_timestamp": maturity_timestamp,
            "hedge_wallet_hash": hedge_wallet_hash or "",
            "hedge_address": contract_metadata["hedgeAddress"],
            "hedge_address_path": hedge_address_path,
            "hedge_pubkey": contract_metadata["hedgePublicKey"],
            "long_wallet_hash": long_wallet_hash or "",
            "long_address": contract_metadata["longAddress"],
            "long_address_path": long_address_path,
            "long_pubkey": contract_metadata["longPublicKey"],
            "oracle_pubkey": contract_metadata["oraclePublicKey"],
            "start_price": contract_metadata["startPrice"],
            "low_liquidation_multiplier": contract_metadata["lowLiquidationPriceMultiplier"],
            "high_liquidation_multiplier": contract_metadata["highLiquidationPriceMultiplier"],
            "funding_tx_hash": "",
            "settlement_service": settlement_service,
            "check_settlement_service": False,
        }

        if position == "hedge":
            validated_data["hedge_funding_proposal"] = funding_proposal
        elif position == "long":
            validated_data["long_funding_proposal"] = funding_proposal

        if contract_data.get("fee", None):
            hedge_position_data["fee"] = {
                "address": contract_data["fee"]["address"],
                "satoshis": contract_data["fee"]["satoshis"],
            }

        hedge_position_serializer = HedgePositionSerializer(data=hedge_position_data)
        hedge_position_serializer.is_valid(raise_exception=True)
        hedge_position_obj = hedge_position_serializer.save()

        # this must be at the last part as much as possible
        funding_response = fund_hedge_position(
            contract_data,
            {
                "txHash": funding_proposal["tx_hash"],
                "txIndex": funding_proposal["tx_index"],
                "txValue": funding_proposal["tx_value"],
                "scriptSig": funding_proposal["script_sig"],
                "publicKey": funding_proposal["pubkey"],
                "inputTxHashes": funding_proposal["input_tx_hashes"],
            },
            oracle_message_sequence,
            position=position,
        )
        if not funding_response["success"]:
            error = "Error in funding hedge position"
            if funding_response.get("error", None):
                error += f". {funding_response['error']}"
            raise serializers.ValidationError(error)

        hedge_position_obj.funding_tx_hash = funding_response["fundingTransactionHash"]
        hedge_position_obj.save()

        return hedge_position_obj


class OracleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Oracle
        fields = [
            "pubkey",
            "asset_name",
            "asset_currency",
            "asset_decimals",
        ]

class PriceOracleMessageSerializer(serializers.ModelSerializer):
    message_timestamp = TimestampField()

    class Meta:
        model = PriceOracleMessage
        fields = [
            "pubkey",
            "message_timestamp",
            "price_value",
            "price_sequence",
            "message_sequence",
        ]