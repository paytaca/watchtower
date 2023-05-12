from rest_framework import serializers
from ..models.peer import Peer

class PeerSerializer(serializers.ModelSerializer):
  class Meta:
    model = Peer
    fields = [
        'id',
        'nickname',
        'is_arbiter',
        'public_key',
        'address',
        'is_disabled',
        'created_at',
        'modified_at'
    ]

class PeerWriteSerializer(serializers.ModelSerializer):
  class Meta:
    model = Peer
    fields = [
        'nickname',
        'wallet_hash',
        'public_key',
        'address',
        'is_arbiter'
    ]