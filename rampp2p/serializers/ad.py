from rest_framework import serializers
from rampp2p.utils.utils import get_trading_fees
from django.db.models import Q, Subquery, OuterRef, F
from rampp2p.models import (
    Ad, 
    AdSnapshot,
    PriceType,
    CooldownChoices,
    Peer,
    FiatCurrency, 
    CryptoCurrency,
    Order, 
    Status, 
    StatusType,
    PaymentMethod,
    MarketRate
)
from .currency import FiatCurrencySerializer, CryptoCurrencySerializer
from .payment import RelatedPaymentMethodSerializer, PaymentMethodSerializer, SubsetPaymentMethodSerializer

class AdSnapshotSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    fiat_currency = FiatCurrencySerializer()
    crypto_currency = CryptoCurrencySerializer()
    payment_methods = RelatedPaymentMethodSerializer(many=True)

    class Meta:
        model = AdSnapshot
        fields = [
            'id',
            'ad',
            'trade_type',
            'price_type',
            'fiat_currency',
            'crypto_currency',
            'floating_price',
            'price',
            'market_price',
            'fixed_price',
            'trade_floor',
            'trade_ceiling',
            'trade_amount',
            'payment_methods',
            'appeal_cooldown_choice',
            'created_at'
        ]

    def get_price(self, instance: AdSnapshot):
        if instance.price_type == PriceType.FIXED:
            return instance.fixed_price
        return instance.market_price * (instance.floating_price/100)

class SubsetAdSnapshotSerializer(AdSnapshotSerializer):
    id = serializers.SerializerMethodField()
    fiat_currency = FiatCurrencySerializer()
    crypto_currency = CryptoCurrencySerializer()
    payment_methods = SubsetPaymentMethodSerializer(many=True)
    appeal_cooldown = serializers.SerializerMethodField()

    class Meta(AdSnapshotSerializer.Meta):
        fields = [
            'id',
            'payment_methods',
            'trade_type',
            'price_type',
            'fiat_currency',
            'crypto_currency',
            'appeal_cooldown',
            'created_at'
        ]
    
    def get_id(self, obj):
        return obj.ad.id
    
    def get_appeal_cooldown(self, obj):
        return obj.appeal_cooldown

class AdListSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    fiat_currency = FiatCurrencySerializer()
    crypto_currency = CryptoCurrencySerializer()
    price = serializers.SerializerMethodField()
    payment_methods = RelatedPaymentMethodSerializer(many=True)
    trade_count = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    appeal_cooldown = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = [
            'id',
            'owner',
            'trade_type',
            'price_type',
            'fiat_currency',
            'crypto_currency',
            'price',
            'trade_floor',
            'trade_ceiling',
            'trade_amount',
            'payment_methods',
            'trade_count',
            'completion_rate',
            'appeal_cooldown',
            'is_owned',
            'is_public',
            'created_at',
            'modified_at'
        ]
    
    def get_appeal_cooldown(self, instance: Ad):
        return CooldownChoices(instance.appeal_cooldown_choice).value
    
    def get_owner(self, instance: Ad):
        return {
            'id': instance.owner.id,
            'name': instance.owner.name,
            'rating':  instance.owner.average_rating()
        }
    
    def get_is_owned(self, instance: Ad):
        wallet_hash = ''
        try:
            wallet_hash = self.context['wallet_hash']
        except KeyError:
            pass
        if instance.owner.wallet_hash == wallet_hash:
            return True
        return False
    
    def get_price(self, instance: Ad):
        if instance.price_type == PriceType.FIXED:
            return instance.fixed_price
        
        currency = instance.fiat_currency.symbol
        market_price = MarketRate.objects.filter(currency=currency)
        if market_price.exists():
            market_price = market_price.first().price
            price = market_price * (instance.floating_price/100)
        else:
            price = None
        return price
    
    def get_trade_count(self, instance: Ad):
        # Count the number of trades (orders) related to ad owner
        query = Q(ad_snapshot__ad__owner__id=instance.owner.id)
        trade_count = Order.objects.filter(query).count()
        return trade_count

    def get_completion_rate(self, instance: Ad):
        ''' 
        completion_rate = released_count / (released_count + canceled_count + refunded_count)
        '''
        
        owner_id = instance.owner.id
        released_count = self.get_orders_status_count(owner_id, StatusType.RELEASED)
        canceled_count = self.get_orders_status_count(owner_id, StatusType.CANCELED)
        refunded_count = self.get_orders_status_count(owner_id, StatusType.REFUNDED)
        
        completion_rate = 0
        denum = released_count + canceled_count + refunded_count        
        if denum > 0:
            completion_rate = released_count / denum * 100
        
        return completion_rate
    
    def get_orders_status_count(self, owner_id: int, status: StatusType):
        # Subquery to get the latest status for each order
        query = Q(order_id=OuterRef('id')) & Q(status=status)
        latest_status_subquery = Status.objects.filter(query).order_by('-created_at').values('id')[:1]
        
        # Retrieve the latest statuses for each order
        user_orders = Order.objects.filter(Q(ad_snapshot__ad__owner__id=owner_id)).annotate(
            latest_status_id = Subquery(latest_status_subquery)
        )

        # Filter only the orders with their latest status
        filtered_orders_count = user_orders.filter(status__id=F('latest_status_id')).count()
        return filtered_orders_count

class AdDetailSerializer(AdListSerializer):
    fees = serializers.SerializerMethodField()

    class Meta(AdListSerializer.Meta):
        fields = AdListSerializer.Meta.fields + [
            'fees',
            'floating_price',
            'fixed_price',
            'trade_amount'
        ]

    def get_fees(self, _):
        _, fees = get_trading_fees()
        return fees
    
class AdOwnerSerializer(AdDetailSerializer):
    payment_methods = PaymentMethodSerializer(many=True)

class AdCreateSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=Peer.objects.all())
    fiat_currency = serializers.PrimaryKeyRelatedField(queryset=FiatCurrency.objects.all())
    crypto_currency = serializers.PrimaryKeyRelatedField(queryset=CryptoCurrency.objects.all())
    payment_methods = serializers.PrimaryKeyRelatedField(queryset=PaymentMethod.objects.all(), many=True)
    appeal_cooldown_choice = serializers.ChoiceField(choices=CooldownChoices.choices,required=True)
    class Meta:
        model = Ad
        fields = [
            'id',
            'owner',
            'trade_type',
            'price_type',
            'fiat_currency',
            'crypto_currency',
            'fixed_price',
            'floating_price',
            'trade_floor',
            'trade_ceiling',
            'trade_amount',
            'appeal_cooldown_choice',
            'payment_methods',
            'is_public',
            'modified_at',
        ]
    
class AdUpdateSerializer(serializers.ModelSerializer):
    payment_methods = serializers.PrimaryKeyRelatedField(queryset=PaymentMethod.objects.all(), many=True)
    appeal_cooldown_choice = serializers.ChoiceField(choices=CooldownChoices.choices)
    class Meta:
        model = Ad
        fields = [
            'price_type',
            'fixed_price',
            'floating_price',
            'trade_floor',
            'trade_ceiling',
            'trade_amount',
            'appeal_cooldown_choice',
            'payment_methods',
            'is_public',
            'modified_at',
        ]