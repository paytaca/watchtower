from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.db import IntegrityError
from django.core.exceptions import ValidationError

import math
import json

from authentication.token import TokenAuthentication

from rampp2p.models import (
    TradeType,
    StatusType,
    Peer,
    Order,
    Contract,
    Transaction,
    Appeal,
    AppealType,
    Arbiter,
    Status
)
import rampp2p.serializers as serializers
from rampp2p.validators import *
from rampp2p.utils.transaction import validate_transaction
from rampp2p.utils.utils import is_order_expired, get_trading_fees
from rampp2p.utils.handler import update_order_status
from rampp2p.utils.notifications import send_push_notification
import rampp2p.utils.websocket as websocket

import logging
logger = logging.getLogger(__name__)
    
class AppealList(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        wallet_hash = request.user.wallet_hash
        try:
            # validate permissions
            self.validate_permissions(wallet_hash)
        except ValidationError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_403_FORBIDDEN)
        
        appeal_state = request.query_params.get('state')
        try:
            limit = int(request.query_params.get('limit', 0))
            page = int(request.query_params.get('page', 1))
        except ValueError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        if limit < 0:
            return Response({'error': 'limit must be a non-negative number'}, status=status.HTTP_400_BAD_REQUEST)
        
        if page < 1:
            return Response({'error': 'invalid page number'}, status=status.HTTP_400_BAD_REQUEST)
        
        arbiter_order_ids = list(Order.objects.filter(arbiter__wallet_hash=wallet_hash).values_list('id', flat=True))
        queryset = Appeal.objects.filter(order__pk__in=arbiter_order_ids).order_by('created_at')

        if appeal_state == 'PENDING':
            queryset = queryset.exclude(resolved_at__isnull=False)
        if appeal_state == 'RESOLVED':
            queryset = queryset.exclude(resolved_at__isnull=True)

        # Count total pages
        count = queryset.count()
        total_pages = page
        if limit > 0:
            total_pages = math.ceil(count / limit)

        # Splice queryset
        offset = (page - 1) * limit
        page_results = queryset[offset:offset + limit]

        serializer = serializers.AppealSerializer(page_results, many=True)
        data = {
            'appeals': serializer.data,
            'count': count,
            'total_pages': total_pages
        }
        return Response(data, status.HTTP_200_OK)

    def validate_permissions(self, wallet_hash):
        '''
        Caller must be an arbiter
        '''
        try:
            Arbiter.objects.get(wallet_hash=wallet_hash)
        except Arbiter.DoesNotExist as err:
            raise ValidationError(err.args[0])        

class AppealRequest(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request, pk):
        wallet_hash = request.user.wallet_hash
        try:
            # validate permissions
            self.validate_permissions(wallet_hash, pk)
        except ValidationError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_403_FORBIDDEN)
        
        serialized_appeal = None
        appeal = Appeal.objects.filter(order=pk)
        if appeal.exists():
            appeal = appeal.first()
            serialized_appeal = serializers.AppealSerializer(appeal)
        
            context = { 'wallet_hash': wallet_hash }
            serialized_order = serializers.OrderSerializer(appeal.order, context=context)
            statuses = Status.objects.filter(order=appeal.order.id).order_by('-created_at')
            serialized_statuses = serializers.StatusSerializer(statuses, many=True)
            contract = Contract.objects.filter(order=appeal.order.id).first()
            serialized_contract = serializers.ContractDetailSerializer(contract)
            transactions = Transaction.objects.filter(contract=contract.id)
            serialized_transactions = serializers.TransactionSerializer(transactions, many=True)
            serialized_ad_snapshot =  serializers.AdSnapshotSerializer(appeal.order.ad_snapshot)

        total_fee, fees = get_trading_fees()
        response = {
            'appeal': serialized_appeal if serialized_appeal is None else serialized_appeal.data,
            'order': serialized_order.data,
            'ad_snapshot': serialized_ad_snapshot.data,
            'statuses': serialized_statuses.data,
            'contract': serialized_contract.data,
            'transactions': serialized_transactions.data,
            'fees': {
                'total': total_fee,
                'fees': fees
            }
        }

        return Response(response, status=status.HTTP_200_OK)
        
    def validate_permissions(self, wallet_hash, pk):
        '''
        Order appeals should only be viewable by the buyer/seller/arbiter.
        '''

        try:
            order = Order.objects.get(pk=pk)
            caller = Arbiter.objects.filter(wallet_hash=wallet_hash)
            if not caller.exists():
                caller = Peer.objects.filter(wallet_hash=wallet_hash)
                if not caller.exists():
                    raise ValidationError('Peer or Arbiter matching query does not exist')
            caller = caller.first()
        except (Order.DoesNotExist, ValidationError) as err:
            raise ValidationError(err.args[0])
        
        if (caller.wallet_hash != order.owner.wallet_hash and
            caller.wallet_hash != order.ad_snapshot.ad.owner.wallet_hash and
            caller.wallet_hash != order.arbiter.wallet_hash):
            raise ValidationError('caller not allowed to view this appeal')
        
        return order
    
    '''
    Submits an appeal for an order.
    Requirements:
        (1) The creator of appeal must be the buyer/seller.
        (2) The order must be expired.
        (3) The latest order status must be one of ['ESCRW', 'PD_PN', 'PD']
    Restrictions:
        (1) The seller cannot appeal once they marked the order as 'PD'
        (2) The seller/buyer cannot appeal once the order is completed (i.e. 'RLS', 'CNCL' or 'RFN')
        (3) The seller/buyer cannot appeal before the funds are escrowed (i.e. status = 'SBM', 'CNF', 'ESCRW_PN')
    '''
    def post(self, request, pk):
        wallet_hash = request.user.wallet_hash
        try:
            if not is_order_expired(pk):
                raise ValidationError('order is not expired')
            
            self.validate_permissions(wallet_hash, pk)
            validate_status_inst_count(StatusType.APPEALED, pk)
            validate_status_progression(StatusType.APPEALED, pk)
            appeal_type = request.data.get('type')
            AppealType(appeal_type)

            peer = Peer.objects.get(wallet_hash=wallet_hash)

        except (ValidationError, ValueError, Peer.DoesNotExist) as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            'order': pk,
            'owner': peer.id,
            'type': appeal_type,
            'reasons': request.data.get('reasons')
        }
        serialized_appeal = serializers.AppealCreateSerializer(data=data)
        if serialized_appeal.is_valid():
            appeal = serialized_appeal.save()
            serialized_appeal = serializers.AppealSerializer(appeal)
            serialized_status = serializers.StatusSerializer(data={
                'status': StatusType.APPEALED,
                'order': pk
            })
            if serialized_status.is_valid():
                serialized_status = serializers.StatusReadSerializer(serialized_status.save())
                response_data = {
                    'appeal': serialized_appeal.data,
                    'status': serialized_status.data
                }
                websocket_msg = {
                    'success' : True,
                    'status': serialized_status.data
                }
                websocket.send_order_update(websocket_msg, pk)

                # send push notifications
                party_a = appeal.order.ad_snapshot.ad.owner.wallet_hash
                party_b = appeal.order.owner.wallet_hash
                arbiter = appeal.order.arbiter.wallet_hash
                recipients = [arbiter]
                if wallet_hash == party_a:
                    recipients.append(party_b)
                if wallet_hash == party_b:
                    recipients.append(party_a)
                message = f'Order {pk} {appeal_type} appealed'
                send_push_notification(recipients, message, extra={ 'order_id': pk })

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({'error': serialized_status.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': serialized_appeal.errors}, status=status.HTTP_400_BAD_REQUEST)        

class AppealPendingRelease(APIView):
    authentication_classes = [TokenAuthentication]

    '''
    Marks an appealed order for release of escrowed funds, updating the order status to RELEASE_PENDING.
    TODO: The order status should automatically be updated to RELEASED when the contract address receives
    an outgoing transaction that matches the requirements of the contract.
    Note: This endpoint must be invoked before the actual transfer of funds.

    Requirements:
        (1) Caller must be the order's arbiter
        (2) Order must have an existing appeal
    '''
    def post(self, request, pk):
        try:
            # Validate permissions
            wallet_hash = request.user.wallet_hash
            self.validate_permissions(wallet_hash, pk)

            # Status validations
            status_type = StatusType.RELEASE_PENDING
            validate_status_inst_count(status_type, pk)
            validate_exclusive_stats(status_type, pk)
            validate_status_progression(status_type, pk)                        

            # Update status to RELEASE_PENDING
            serialized_status = update_order_status(pk, status_type)

            contract = Contract.objects.get(order__id=pk)
            _, _ = Transaction.objects.get_or_create(
                contract=contract,
                action=Transaction.ActionType.RELEASE,
            )
            
        except (ValidationError, Contract.DoesNotExist) as err:
            return Response({"success": False, "error": err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        # notify order update subscribers
        websocket_msg = {
            'success' : True,
            'status': serialized_status.data
        }
        websocket.send_order_update(websocket_msg, pk)

        return Response(serialized_status.data, status=status.HTTP_200_OK)
    
    def validate_permissions(self, wallet_hash, pk):
        '''
        Validates if:
            (1) Caller is the order's arbiter
            (2) Order has an existing appeal
        '''
        prefix = "ValidationError:"

        try:
            order = Order.objects.get(pk=pk)
            curr_status = Status.objects.filter(order=order).latest('created_at')
        except Order.DoesNotExist as err:
            raise ValidationError(f'{prefix} {err.args[0]}')
        
        # Raise error if caller is not order's arbiter
        if wallet_hash != order.arbiter.wallet_hash:
            raise ValidationError(f'{prefix} Caller must be order arbiter.')
        
        # Raise error if order's current status is not APPEALED
        if curr_status.status != StatusType.APPEALED:
            raise ValidationError(f'{prefix} action requires status={StatusType.APPEALED.label}')

class AppealPendingRefund(APIView):
    authentication_classes = [TokenAuthentication]

    '''
    Marks an appealed order for refund, updating the order status to REFUND_PENDING.
    TODO: The order status should automatically be updated to REFUNDED when the contract 
    address receives an outgoing transaction that matches the requisites of the contract.
    Note: This endpoint must be invoked before the actual transfer of funds.

    Requirements:
        (1) Caller must be the order's arbiter
        (2) Order must have an existing appeal
    '''
    def post(self, request, pk):
        
        try:
            # Validate permissions
            wallet_hash = request.user.wallet_hash
            self.validate_permissions(wallet_hash, pk)
        
            # Status validations
            status_type = StatusType.REFUND_PENDING
            validate_status_inst_count(status_type, pk)
            validate_exclusive_stats(status_type, pk)
            validate_status_progression(status_type, pk)

            # Update status to REFUND_PENDING
            serialized_status = update_order_status(pk, status_type)

            contract = Contract.objects.get(order__id=pk)
            _, _ = Transaction.objects.get_or_create(
                contract=contract,
                action=Transaction.ActionType.REFUND,
            )
            
        except (ValidationError, Contract.DoesNotExist) as err:
            return Response({"success": False, "error": err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
        
        # notify order update subscribers
        websocket_msg = {
            'success' : True,
            'status': serialized_status.data
        }
        websocket.send_order_update(websocket_msg, pk)
        
        return Response(serialized_status.data, status=status.HTTP_200_OK)
    
    def validate_permissions(self, wallet_hash, pk):
        '''
        Validates if:
            (1) Caller is the order's arbiter
            (2) Order has an existing appeal
        '''
        prefix = "ValidationError:"

        try:
            order = Order.objects.get(pk=pk)
            curr_status = Status.objects.filter(order=order).latest('created_at')
        except Order.DoesNotExist as err:
            raise ValidationError(f'{prefix} {err.args[0]}')
        
        # Raise error if caller is not order's arbiter
        if wallet_hash != order.arbiter.wallet_hash:
            raise ValidationError(f'{prefix} Caller must be order arbiter.')
        
        # Raise error if order's current status is not APPEALED
        if curr_status.status != StatusType.APPEALED:
            raise ValidationError(f'{prefix} action requires status={StatusType.APPEALED.label}')

class VerifyRelease(APIView):
    authentication_classes = [TokenAuthentication]

    '''
    Manually marks the order as (status) RELEASED by validating if a given transaction id (txid) 
    satisfies the prerequisites of its contract.
    Note: This endpoint should only be used as fallback for the ReleaseCrypto endpoint.

    Requirements:
        (1) Caller must be the order's arbiter or seller
        (2) The order's current status must be RELEASE_PENDING (created by calling ReleaseCrypto endpoint first)
        (3) TODO: An amount of time must already have passed since status RELEASE_PENDING was created
    '''
    def post(self, request, pk):
        try:
            # Validate permissions
            self.validate_permissions(request.user.wallet_hash, pk)

            # status validations
            status_type = StatusType.RELEASED
            validate_status_inst_count(status_type, pk)
            validate_exclusive_stats(status_type, pk)
            validate_status_progression(status_type, pk)      
            
            txid = request.data.get('txid')
            if txid is None:
                raise ValidationError('txid field is required')

            contract = Contract.objects.get(order__id=pk)
            
            # Validate the transaction
            validate_transaction(txid, Transaction.ActionType.RELEASE, contract.id)
            
        except (ValidationError, Contract.DoesNotExist, IntegrityError) as err:
            return Response({"success": False, "error": err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
  
        return Response(status=status.HTTP_200_OK)
    
    def validate_permissions(self, wallet_hash, pk):
        '''
        Validates if:
            (1) caller is the order's arbiter/seller,
            (2) the order's current status is RELEASE_PENDING or PAID
        '''
        prefix = "ValidationError:"

        try:
            order = Order.objects.get(pk=pk)
            curr_status = Status.objects.filter(order=order).latest('created_at')
        except Order.DoesNotExist as err:
            raise ValidationError(f'{prefix} {err.args[0]}')
        
        is_arbiter = False
        is_seller = False
        if wallet_hash == order.arbiter.wallet_hash:
            is_arbiter = True
        if order.ad_snapshot.trade_type == TradeType.SELL:
            seller = order.ad_snapshot.ad.owner
        else:
            seller = order.owner
        if wallet_hash == seller.wallet_hash:
            is_seller = True

        if (not is_arbiter) and (not is_seller):
            raise ValidationError(f'{prefix} Caller is not seller nor arbiter.')
        
        if not (curr_status.status == StatusType.RELEASE_PENDING or curr_status.status == StatusType.PAID):
            raise ValidationError(f'{prefix} action requires status {StatusType.RELEASE_PENDING.label} or {StatusType.PAID.label}')

class VerifyRefund(APIView):
    authentication_classes = [TokenAuthentication]
        
    '''
    Manually marks the order as (status) REFUNDED by validating if a given transaction id (txid) 
    satisfies the prerequisites of its contract.
    Note: This endpoint should only be used as fallback for the RefundCrypto endpoint.

    Requirements:
        (1) Caller must be the order's arbiter
        (2) The order's current status must be REFUND_PENDING (created by calling RefundCrypto endpoint first)
        (3) TODO: An amount of time must already have passed since status REFUND_PENDING was created
    '''
    def post(self, request, pk):

        try:
            # validate permissions
            self.validate_permissions(request.user.wallet_hash, pk)
        except ValidationError as err:
            return Response({"success": False, "error": err.args[0]}, status=status.HTTP_403_FORBIDDEN)

        try:
            # status validations
            status_type = StatusType.REFUNDED
            validate_status_inst_count(status_type, pk)
            validate_exclusive_stats(status_type, pk)
            validate_status_progression(status_type, pk)            
            
            txid = request.data.get('txid')
            if txid is None:
                raise ValidationError('txid field is required')

            contract = Contract.objects.get(order__id=pk)
            transaction, _ = Transaction.objects.get_or_create(
                contract=contract,
                action=Transaction.ActionType.REFUND,
                txid=txid
            )

            # Validate the transaction
            validate_transaction(transaction.txid, Transaction.ActionType.REFUND, contract.id)
            
        except (ValidationError, Contract.DoesNotExist, IntegrityError) as err:
            return Response({"success": False, "error": err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
  
        return Response(status=status.HTTP_200_OK)
    
    def validate_permissions(self, wallet_hash, pk):
        '''
        Validates if:
            (1) caller is not the order's arbiter,
            (2) the order's current status is not REFUND_PENDING
        '''
        prefix = "ValidationError:"

        try:
            order = Order.objects.get(pk=pk)
            curr_status = Status.objects.filter(order=order).latest('created_at')
        except Peer.DoesNotExist or Order.DoesNotExist as err:
            raise ValidationError(f'{prefix} {err.args[0]}')
        
        if wallet_hash != order.arbiter.wallet_hash:
            raise ValidationError(f'{prefix} Caller must be order arbiter.')
        
        if (curr_status.status != StatusType.REFUND_PENDING):
            raise ValidationError(f'{prefix} action requires status={StatusType.REFUND_PENDING.label}')
