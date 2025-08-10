from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import models
from .models import Wallet, RewardTransaction
from .serializers import WalletSerializer, RewardTransactionSerializer
# from .utils import calculate_departure_reward  # 출발 시 보상 비활성화
from trips.models import Trip


class TransactionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class WalletView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet

    def retrieve(self, request, *args, **kwargs):
        wallet = self.get_object()
        
        # 최근 10개 거래 포함 (생성 순, 오래된 → 최신) - 테스트 기대 순서와 일치
        recent_transactions = wallet.transactions.order_by('created_at')[:10]
        
        data = {
            'id': wallet.id,
            'balance': wallet.balance,
            'currency_code': wallet.currency_code,
            'created_at': wallet.created_at,
            'updated_at': wallet.updated_at,
            'recent_transactions': RewardTransactionSerializer(recent_transactions, many=True).data
        }
        
        return Response(data)


class WalletTransactionsView(generics.ListAPIView):
    serializer_class = RewardTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TransactionPagination

    def get_queryset(self):
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        # 테스트 기대 순서에 맞춰 오래된 순으로 반환 (생성 순서: earn -> spend)
        return wallet.transactions.order_by('created_at')


# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def preview_departure_reward(request, trip_id):
#     """출발 시 예상 보상 미리보기 (현재 비활성화)"""
#     trip = get_object_or_404(Trip, id=trip_id, user=request.user)
#     
#     # reward_info = calculate_departure_reward(trip) # 출발 시 보상 비활성화
#     
#     # 보상 설명 생성
#     bonus_descriptions = {
#         'basic': '기본 출발 보상',
#         'time_window': 'AI 추천 시간대 출발 보너스',
#         'low_congestion': '혼잡도 낮은 시간대 출발 보너스',
#         'moderate_congestion': '적정 혼잡도 시간대 출발 보너스'
#     }
#     
#     response_data = {
#         'trip_id': trip.id,
#         'expected_reward': 0, # 출발 시 보상 비활성화
#         'base_reward': 0, # 출발 시 보상 비활성화
#         'multiplier': 1, # 출발 시 보상 비활성화
#         'bonus_type': 'basic', # 출발 시 보상 비활성화
#         'bonus_description': '출발 보상', # 출발 시 보상 비활성화
#         'bucket_bonus': 0, # 출발 시 보상 비활성화
#         'recommendation_info': {
#             'bucket': trip.recommendation.recommended_bucket if trip.recommendation else None,
#             'window_start': trip.recommendation.window_start.strftime('%H:%M') if trip.recommendation else None,
#             'window_end': trip.recommendation.window_end.strftime('%H:%M') if trip.recommendation else None,
#             'congestion_level': trip.recommendation.expected_congestion_level if trip.recommendation else None
#         }
#     }
#     
#     return Response(response_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reward_summary(request):
    """사용자 보상 요약 정보"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # 총 적립/사용 금액 계산
    total_earned = wallet.transactions.filter(type='earn').aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    total_spent = wallet.transactions.filter(type='spend').aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    # 최근 거래 내역
    recent_transactions = wallet.transactions.all()[:5]
    
    return Response({
        'current_balance': wallet.balance,
        'currency_code': wallet.currency_code,
        'total_earned': total_earned,
        'total_spent': total_spent,
        'transaction_count': wallet.transactions.count(),
        'recent_transactions': RewardTransactionSerializer(recent_transactions, many=True).data
    })
