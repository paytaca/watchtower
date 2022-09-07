from django.db import models

# Create your models here.
class LongAccount(models.Model):
    wallet_hash = models.CharField(max_length=100, unique=True)
    address_path = models.CharField(max_length=10)
    address = models.CharField(max_length=75)
    pubkey = models.CharField(max_length=75)

    # balance = models.BigIntegerField(null=True, blank=True)

    min_auto_accept_duration = models.IntegerField(default=0)
    max_auto_accept_duration = models.IntegerField(default=0)
    auto_accept_allowance = models.BigIntegerField(default=0)


class HedgeFundingProposal(models.Model):
    tx_hash = models.CharField(max_length=75)
    tx_index = models.IntegerField()
    tx_value = models.BigIntegerField()
    script_sig = models.TextField()


class HedgePosition(models.Model):
    address = models.CharField(max_length=75, unique=True)
    anyhedge_contract_version = models.CharField(max_length=20)

    satoshis = models.BigIntegerField()

    start_timestamp = models.DateTimeField()
    maturity_timestamp = models.DateTimeField()

    hedge_wallet_hash = models.CharField(max_length=75)
    hedge_address = models.CharField(max_length=75)
    hedge_pubkey = models.CharField(max_length=75)
    long_wallet_hash = models.CharField(max_length=75)
    long_address = models.CharField(max_length=75)
    long_pubkey = models.CharField(max_length=75)

    oracle_pubkey = models.CharField(max_length=75)

    start_price = models.IntegerField()
    low_liquidation_multiplier = models.FloatField()
    high_liquidation_multiplier = models.FloatField()

    # low_liquidation_price = models.IntegerField()
    # high_liquidation_price = models.IntegerField()

    funding_tx_hash = models.CharField(max_length=75, null=True, blank=True)
    hedge_funding_proposal = models.OneToOneField(
        HedgeFundingProposal,
        related_name="hedge_position",
        on_delete=models.CASCADE,
        null=True, blank=True,
    )
    long_funding_proposal = models.OneToOneField(
        HedgeFundingProposal,
        related_name="long_position",
        on_delete=models.CASCADE,
        null=True, blank=True,
    )


    @property
    def low_liquidation_price(self):
        return round(self.start_price * self.low_liquidation_multiplier)

    @property
    def high_liquidation_price(self):
        return round(self.start_price * self.high_liquidation_multiplier)

    @property
    def total_sats(self):
        return round((self.satoshis * self.start_price) / self.low_liquidation_price)

    @property
    def long_input_sats(self):
        return self.total_sats - self.satoshis


class HedgePositionOffer(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SETTLED = "settled"
    STATUS_CANCELLED = "cancelled"

    STATUSES = [
        STATUS_PENDING,
        STATUS_SETTLED,
        STATUS_CANCELLED,
    ]

    STATUSES = [(STATUS, STATUS.replace('_', ' ').capitalize()) for STATUS in STATUSES]
    status = models.CharField(max_length=15, choices=STATUSES, default=STATUS_PENDING)

    wallet_hash = models.CharField(max_length=100)
    satoshis = models.BigIntegerField()

    duration_seconds = models.IntegerField()
    high_liquidation_multiplier = models.FloatField()
    low_liquidation_multiplier = models.FloatField()

    hedge_address = models.CharField(max_length=75)
    hedge_pubkey = models.CharField(max_length=75)
    hedge_position = models.OneToOneField(
        HedgePosition,
        related_name="position_offer",
        on_delete=models.CASCADE,
        null=True, blank=True
    )

    auto_settled = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)