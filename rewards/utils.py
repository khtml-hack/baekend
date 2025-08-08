"""
Reward utility functions
"""
from django.db import transaction
from .models import Wallet, RewardTransaction


def create_reward_transaction(user, trip=None, transaction_type='earn', amount=0, description=''):
    """
    리워드 거래 생성 및 지갑 잔액 업데이트
    
    Args:
        user: 사용자 객체
        trip: 여행 객체 (선택사항)
        transaction_type: 'earn' 또는 'spend'
        amount: 금액 (양수)
        description: 거래 설명
    
    Returns:
        RewardTransaction: 생성된 거래 객체
    """
    with transaction.atomic():
        # 지갑 가져오기 또는 생성
        wallet, created = Wallet.objects.get_or_create(user=user)
        
        # 거래 생성
        reward_transaction = RewardTransaction.objects.create(
            wallet=wallet,
            trip=trip,
            type=transaction_type,
            amount=amount,
            description=description
        )
        
        # 지갑 잔액 업데이트
        if transaction_type == 'earn':
            wallet.balance += amount
        elif transaction_type == 'spend':
            wallet.balance -= amount
            # 잔액 부족 체크
            if wallet.balance < 0:
                raise ValueError("잔액이 부족합니다.")
        
        wallet.save()
        
        return reward_transaction


def reward_for_trip_completion(user, trip, base_amount=100):
    """
    여행 완료 시 리워드 지급
    
    Args:
        user: 사용자 객체
        trip: 완료된 여행 객체
        base_amount: 기본 리워드 금액
    
    Returns:
        RewardTransaction: 생성된 리워드 거래
    """
    description = f"여행 완료 리워드 - {trip.recommendation.origin_address} → {trip.recommendation.destination_address}"
    
    return create_reward_transaction(
        user=user,
        trip=trip,
        transaction_type='earn',
        amount=base_amount,
        description=description
    )
