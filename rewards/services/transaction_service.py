from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth import get_user_model
from ..models import Wallet, RewardTransaction

User = get_user_model()


def get_user_balance(user):
    """사용자의 현재 잔액 조회"""
    try:
        wallet = Wallet.objects.get(user=user)
        return wallet.balance
    except Wallet.DoesNotExist:
        return 0


def get_or_create_wallet(user):
    """사용자의 지갑을 가져오거나 생성"""
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={'balance': 0}
    )
    return wallet


@transaction.atomic
def create_transaction(user, amount, transaction_type, description, merchant_info=None):
    """
    리워드 거래 생성
    
    Args:
        user: 사용자 객체
        amount: 거래 금액
        transaction_type: 거래 타입 ('earn' 또는 'spend')
        description: 거래 설명
        merchant_info: 상점 정보 (선택사항)
    
    Returns:
        RewardTransaction: 생성된 거래 객체
    """
    wallet = get_or_create_wallet(user)
    
    # 금액을 정수로 변환 (BigIntegerField)
    if not isinstance(amount, int):
        amount = int(amount)
    
    # 사용 거래인 경우 잔액 확인
    if transaction_type == 'spend':
        if wallet.balance < amount:
            raise ValueError(f"잔액이 부족합니다. 현재 잔액: {wallet.balance}원")
        
        # 잔액 차감
        wallet.balance -= amount
    elif transaction_type == 'earn':
        # 잔액 증가
        wallet.balance += amount
    else:
        raise ValueError("transaction_type은 'earn' 또는 'spend'여야 합니다.")
    
    wallet.save()
    
    # 거래 기록 생성 (실제 모델 필드에 맞게)
    transaction_obj = RewardTransaction.objects.create(
        wallet=wallet,
        type=transaction_type,  # 'type' 필드 사용
        amount=amount,
        description=description
    )
    
    return transaction_obj


def process_reward_earning(user, amount, reason):
    """
    리워드 적립 처리
    
    Args:
        user: 사용자 객체
        amount: 적립할 금액
        reason: 적립 사유
    
    Returns:
        dict: 처리 결과
    """
    try:
        transaction_obj = create_transaction(
            user=user,
            amount=amount,
            transaction_type='earn',
            description=reason
        )
        
        return {
            'success': True,
            'transaction_id': transaction_obj.id,
            'amount': transaction_obj.amount,
            'new_balance': get_user_balance(user),
            'message': f"{amount}원이 적립되었습니다."
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def process_reward_spending(user, amount, merchant_info, description):
    """
    리워드 사용 처리
    
    Args:
        user: 사용자 객체
        amount: 사용할 금액
        merchant_info: 상점 정보
        description: 사용 설명
    
    Returns:
        dict: 처리 결과
    """
    try:
        transaction_obj = create_transaction(
            user=user,
            amount=amount,
            transaction_type='spend',
            description=description,
            merchant_info=merchant_info
        )
        
        return {
            'success': True,
            'transaction_id': transaction_obj.id,
            'amount': transaction_obj.amount,
            'new_balance': get_user_balance(user),
            'message': f"{amount}원이 사용되었습니다."
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_transaction_history(user, limit=50, transaction_type=None):
    """
    사용자의 거래 내역 조회
    
    Args:
        user: 사용자 객체
        limit: 조회할 최대 개수
        transaction_type: 거래 타입 필터
    
    Returns:
        QuerySet: 거래 내역
    """
    queryset = RewardTransaction.objects.filter(user=user)
    
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)
    
    return queryset.order_by('-created_at')[:limit]


def calculate_total_earned(user):
    """사용자의 총 적립 금액 계산"""
    total = RewardTransaction.objects.filter(
        user=user,
        transaction_type='earn',
        status='completed'
    ).aggregate(total=Sum('amount'))['total']
    
    return total or Decimal('0.00')


def calculate_total_spent(user):
    """사용자의 총 사용 금액 계산"""
    total = RewardTransaction.objects.filter(
        user=user,
        transaction_type='spend',
        status='completed'
    ).aggregate(total=Sum('amount'))['total']
    
    return total or Decimal('0.00')
