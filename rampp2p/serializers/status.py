from rest_framework import serializers
from rampp2p.models import (
    Status,
    Order
)
class StatusSerializer(serializers.ModelSerializer):
  order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
  seller_read_at = serializers.DateTimeField(required=False)
  buyer_read_at = serializers.DateTimeField(required=False)

  class Meta:
    model = Status
    fields = [
      'id',
      'status',
      'order',
      'created_at',
      'seller_read_at',
      'buyer_read_at'
    ]

class StatusReadSerializer(serializers.ModelSerializer):
  order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
  status = serializers.SerializerMethodField()
  class Meta:
    model = Status
    fields = [
      'id',
      'status',
      'order',
      'created_at',
      'seller_read_at',
      'buyer_read_at'
    ]
  
  def get_status(self, instance: Status):
    return {
      'label': instance.get_status_display(),
      'value': instance.status
    }