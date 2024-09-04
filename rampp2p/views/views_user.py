from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from authentication.token import TokenAuthentication
from authentication.serializers import UserSerializer

import rampp2p.serializers as rampp2p_serializers
import rampp2p.models as rampp2p_models
from rampp2p.viewcodes import ViewCode
from rampp2p.utils.signature import verify_signature, get_verification_headers

import math
from datetime import datetime, timedelta

import logging
logger = logging.getLogger(__name__)

class UserProfileView(APIView):
    def get(self, request):
        wallet_hash = request.headers.get('wallet_hash')
        if wallet_hash is None:
            return Response({'error': 'wallet_hash is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        is_arbiter = False
        arbiter = rampp2p_models.Arbiter.objects.filter(wallet_hash=wallet_hash)
        
        if arbiter.exists():
            user = rampp2p_serializers.ArbiterSerializer(arbiter.first()).data
            is_arbiter = True
        
        if not is_arbiter:
            peer = rampp2p_models.Peer.objects.filter(wallet_hash=wallet_hash)
            if peer.exists():    
                user = rampp2p_serializers.PeerProfileSerializer(peer.first()).data
            
        response = {
            "is_arbiter": is_arbiter,
            "user": user
        }
        return Response(response, status.HTTP_200_OK)
    
class ArbiterListCreateView(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        queryset = rampp2p_models.Arbiter.objects.filter(
                Q(is_disabled=False) &
                (Q(inactive_until__isnull=True) |
                 Q(inactive_until__lte=datetime.now())))

        # Filter by currency. Default to arbiter for PHP if not set
        currency = request.query_params.get('currency') or 'PHP'
        if not currency:
            return Response({'error': 'currency is required'}, status.HTTP_400_BAD_REQUEST)
        queryset = queryset.filter(fiat_currencies__symbol=currency)

        # Filter by arbiter id
        id = request.query_params.get('id')
        if id:
            queryset = queryset.filter(id=id)

        serializer = rampp2p_serializers.ArbiterSerializer(queryset, many=True)
        return Response(serializer.data, status.HTTP_200_OK)
    
    def post(self, request):
        public_key = request.data.get('public_key')
        if public_key is None:
            return Response({'error': 'public_key is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # validate signature
        signature, timestamp, wallet_hash = get_verification_headers(request)
        message = ViewCode.ARBITER_CREATE.value + '::' + timestamp
        verify_signature(wallet_hash, signature, message, public_key=public_key)
        
        peer = rampp2p_models.Peer.objects.filter(wallet_hash=wallet_hash)
        if peer.exists():
            return Response({'error': 'Users cannot be both Peer and Arbiter'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data.copy()
        data['wallet_hash'] = wallet_hash

        serialized_arbiter = rampp2p_serializers.ArbiterSerializer(data=data)
        if not serialized_arbiter.is_valid():
            return Response(serialized_arbiter.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            serialized_arbiter = rampp2p_serializers.ArbiterSerializer(serialized_arbiter.save())
        except IntegrityError:
            return Response({'error': 'arbiter with wallet_hash already exists'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialized_arbiter.data, status=status.HTTP_200_OK)

class ArbiterDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    
    def get(self, request):
        arbiter_id = request.data.get('arbiter_id')
        wallet_hash = request.user.wallet_hash
        try:
            arbiter = None
            if arbiter_id:
                arbiter = rampp2p_models.Arbiter.objects.get(pk=arbiter_id)
            else:
                arbiter = rampp2p_models.Arbiter.objects.get(wallet_hash=wallet_hash)
        except rampp2p_models.Arbiter.DoesNotExist as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(rampp2p_serializers.ArbiterSerializer(arbiter).data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        data = request.data.copy()
        
        inactive_hours = request.data.get('inactive_hours')
        if inactive_hours:
            data['inactive_until'] = datetime.now() + timedelta(hours=inactive_hours)
        
        serializer = rampp2p_serializers.ArbiterSerializer(request.user, data=data)
        if serializer.is_valid():
            serializer = rampp2p_serializers.ArbiterSerializer(serializer.save())
            return Response(serializer.data, status=status.HTTP_200_OK)        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PeerCreateView(APIView):
    def post(self, request):
        try:
            signature, timestamp, wallet_hash = get_verification_headers(request)
            public_key = request.headers.get('public_key')
            
            message = ViewCode.PEER_CREATE.value + '::' + timestamp
            verify_signature(wallet_hash, signature, message, public_key=public_key)
        except Exception as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        arbiter = rampp2p_models.Arbiter.objects.filter(wallet_hash=wallet_hash)
        if arbiter.exists():
            return Response({'error': 'Users cannot be both Peer and Arbiter'}, status=status.HTTP_400_BAD_REQUEST)

        # check if username is reserved
        prefix = 'reserved-'
        reserved = None
        username = request.data.get('name')
        duplicate_name_error = False
        if (username.startswith(prefix)):
            subset_key = username[len(prefix):]
            reserved_name = rampp2p_models.ReservedName.objects.filter(key=subset_key)
            if reserved_name.exists():
                # accept key if reserved name is not yet associated with a Peer
                if reserved_name.first().peer is None:
                    reserved = reserved_name.first()
                    username = reserved.name
                else:
                    duplicate_name_error = True
            else:
                return Response({'error': 'no such reserved username'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # check if username already exists
            if (rampp2p_models.Peer.objects.filter(name__iexact=username).exists() or
                rampp2p_models.ReservedName.objects.filter(name__iexact=username).exists()):
                duplicate_name_error = True
        
        if duplicate_name_error:
            return Response({'error': 'similar username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        # create new Peer instance
        data = request.data.copy()
        data['name'] = username
        data['wallet_hash'] = wallet_hash
        data['public_key'] = public_key
        
        serializer = rampp2p_serializers.PeerCreateSerializer(data=data)
        if serializer.is_valid():
            peer = serializer.save()
            serializer = rampp2p_serializers.PeerSerializer(peer)
            if reserved:
                reserved.peer = peer
                reserved.redeemed_at = timezone.now()
                reserved.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PeerDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    
    def get(self, request):
        id = request.query_params.get('id')
        try:
            peer = rampp2p_models.Peer.objects.get(id=id)
        except rampp2p_models.Peer.DoesNotExist:
            raise Http404
        serializer = rampp2p_serializers.PeerSerializer(peer)
        return Response(serializer.data, status.HTTP_200_OK)

    def patch(self, request):        
        serializer = rampp2p_serializers.PeerUpdateSerializer(request.user, data=request.data)
        if serializer.is_valid():
            peer = serializer.save()
            user_info = {
                'id': peer.id,
                'chat_identity_id': peer.chat_identity_id,
                'public_key': peer.public_key,
                'name': peer.name,
                'address': peer.address,
                'address_path': peer.address_path
            }
            return Response(UserSerializer(user_info).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ArbiterFeedbackView(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        queryset = rampp2p_models.ArbiterFeedback.objects.all()

        order_id = request.query_params.get('order_id')
        from_peer = request.query_params.get('from_peer')
        to_peer = request.query_params.get('to_peer')
        arbiter = request.query_params.get('arbiter')
        rating = request.query_params.get('rating')
        ad_id = request.query_params.get('ad_id')

        try:
            limit = int(request.query_params.get('limit', 0))
            page = int(request.query_params.get('page', 1))
        except ValueError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        if limit < 0:
            return Response({'error': 'limit must be a non-negative number'}, status=status.HTTP_400_BAD_REQUEST)
        
        if page < 1:
            return Response({'error': 'invalid page number'}, status=status.HTTP_400_BAD_REQUEST)
        
        if ad_id is not None:
            queryset = queryset.filter(Q(order__ad_snapshot__ad_id=ad_id))
        
        if order_id is not None:
            queryset = queryset.filter(Q(order=order_id))

        if from_peer is not None:
            queryset = queryset.filter(Q(from_peer=from_peer))
        
        if to_peer is not None:
            queryset = queryset.filter(Q(to_peer=to_peer))
        
        if arbiter is not None:
            queryset = queryset.filter(Q(to_arbiter=arbiter))
        
        if rating is not None:
            queryset = queryset.filter(Q(rating=rating))

        # pagination
        count = queryset.count()
        total_pages = page
        if limit > 0:
            total_pages = math.ceil(count / limit)

        offset = (page - 1) * limit
        paged_queryset = queryset[offset:offset + limit]

        serializer = rampp2p_serializers.ArbiterFeedbackSerializer(paged_queryset, many=True)
        data = {
            'feedbacks': serializer.data,
            'count': count,
            'total_pages': total_pages
        }
        return Response(data, status.HTTP_200_OK)

    def post(self, request):
        try:
            order_id = request.data.get('order_id')
            from_peer, arbiter, order = self.validate_permissions(request.user.wallet_hash, order_id)
            self.validate_limit(from_peer, order)
        except (AssertionError, rampp2p_models.Peer.DoesNotExist, rampp2p_models.Order.DoesNotExist) as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: block feedback if order is not yet completed
        if arbiter is None:
            return Response({'error': 'order not completed yet'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['order'] = order.id
        data['from_peer'] = from_peer.id
        data['to_arbiter'] = arbiter.id
        logger.warn(f'data: {data}')
        
        serializer = rampp2p_serializers.ArbiterFeedbackCreateSerializer(data=data)
        if serializer.is_valid():                        
            serializer = rampp2p_serializers.ArbiterFeedbackCreateSerializer(serializer.save())
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def validate_limit(self, from_peer, order):
        '''
        Limits feedback to 1 per order peer.
        '''
        feedback_count = (rampp2p_models.ArbiterFeedback.objects.filter(Q(order=order) & Q(from_peer=from_peer))).count()
        assert feedback_count == 0, 'peer feedback already existing'
    
    def validate_permissions(self, wallet_hash, pk):
        '''
        Validates if from_peer is allowed to create an arbiter feedback for this order.
        ''' 
        try:
            from_peer = rampp2p_models.Peer.objects.get(wallet_hash=wallet_hash)
            order = rampp2p_models.Order.objects.get(pk=pk)
        except (rampp2p_models.Peer.DoesNotExist, rampp2p_models.Order.DoesNotExist) as err:
            raise ValidationError(err.args[0])

        order_creator = order.owner.id == from_peer.id
        order_ad_creator = order.ad_snapshot.ad.owner.id == from_peer.id

        if not (order_creator or order_ad_creator):
            raise ValidationError('not allowed to feedback this order')
        
        arbiter = order.arbiter
        return from_peer, arbiter, order
    
class PeerFeedbackView(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        queryset = rampp2p_models.Feedback.objects.all()

        ad_id = request.query_params.get('ad_id')
        order_id = request.query_params.get('order_id')
        from_peer = request.query_params.get('from_peer', None)
        to_peer = request.query_params.get('to_peer', None)
        rating = request.query_params.get('rating', None)

        try:
            limit = int(request.query_params.get('limit', 0))
            page = int(request.query_params.get('page', 1))
        except ValueError as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)

        if limit < 0:
            return Response({'error': 'limit must be a non-negative number'}, status=status.HTTP_400_BAD_REQUEST)
        
        if page < 1:
            return Response({'error': 'invalid page number'}, status=status.HTTP_400_BAD_REQUEST)
        
        if ad_id is not None:
            queryset = queryset.filter(Q(order__ad_snapshot__ad_id=ad_id))
        
        if order_id is not None:
            queryset = queryset.filter(Q(order=order_id))
        
        if from_peer is not None:
            queryset = queryset.filter(Q(from_peer=from_peer))
        
        if to_peer is not None:
            queryset = queryset.filter(Q(to_peer=to_peer))
        
        if rating is not None:
            queryset = queryset.filter(Q(rating=rating))

        # pagination
        count = queryset.count()
        total_pages = page
        if limit > 0:
            total_pages = math.ceil(count / limit)

        offset = (page - 1) * limit
        paged_queryset = queryset[offset:offset + limit]

        serializer = rampp2p_serializers.FeedbackSerializer(paged_queryset, many=True)
        data = {
            'feedbacks': serializer.data,
            'count': count,
            'total_pages': total_pages
        }

        return Response(data, status.HTTP_200_OK)

    def post(self, request):
        try:
            order_id = request.data.get('order_id')
            from_peer, to_peer, order = self.validate_permissions(request.user.wallet_hash, order_id)

            data = request.data.copy()
            data['from_peer'] = from_peer.id
            data['to_peer'] = to_peer.id
            data['order'] = order.id
            self.validate_limit(data['from_peer'], data['to_peer'], data['order'])
        except (AssertionError, rampp2p_models.Peer.DoesNotExist, rampp2p_models.Order.DoesNotExist) as err:
            return Response({'error': err.args[0]}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = rampp2p_serializers.FeedbackCreateSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def validate_limit(self, from_peer, to_peer, order):
        '''
        Validates that from_peer can only create 1 feedback for the order.
        '''
        feedback_count = (rampp2p_models.Feedback.objects.filter(Q(from_peer=from_peer) & Q(to_peer=to_peer) & Q(order=order))).count()
        assert feedback_count == 0, 'peer feedback already existing'
    
    def validate_permissions(self, wallet_hash, pk):
        '''
        Validates if from_peer is allowed to create a peer feedback for this order.
        ''' 
        try:
            from_peer = rampp2p_models.Peer.objects.get(wallet_hash=wallet_hash)
            order = rampp2p_models.Order.objects.get(pk=pk)
        except (rampp2p_models.Peer.DoesNotExist, rampp2p_models.Order.DoesNotExist) as err:
            raise ValidationError(err.args[0])

        order_creator = order.owner.id == from_peer.id
        order_ad_creator = order.ad_snapshot.ad.owner.id == from_peer.id

        if not (order_creator or order_ad_creator):
            raise ValidationError('not allowed to feedback this order')
        
        to_peer = None
        if order_creator:
            to_peer = order.ad_snapshot.ad.owner
        else:
            to_peer = order.owner
        
        return from_peer, to_peer, order
    
class FeedbackDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [TokenAuthentication]
    queryset = rampp2p_models.Feedback.objects.all()
    serializer_class = rampp2p_serializers.FeedbackSerializer
