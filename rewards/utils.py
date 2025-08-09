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


def calculate_departure_reward(trip):
    """
    AI 추천 기반 출발 시간 보상 계산
    
    Args:
        trip: 여행 객체
    
    Returns:
        dict: 보상 정보 {'amount': int, 'bonus_type': str, 'multiplier': float}
    """
    if not trip.recommendation or not trip.started_at:
        return {'amount': 0, 'bonus_type': 'none', 'multiplier': 1.0}
    
    base_reward = 100
    multiplier = 1.0
    bonus_type = 'basic'
    
    # 추천 시간 윈도우 체크
    recommendation = trip.recommendation
    departure_time = trip.started_at.time()
    
    # 추천 시간대 내 출발 보너스
    if recommendation.window_start <= departure_time <= recommendation.window_end:
        multiplier += 0.3  # 30% 보너스
        bonus_type = 'time_window'
    
    # 혼잡도 기반 보너스
    congestion_level = recommendation.expected_congestion_level
    if congestion_level:
        if congestion_level <= 2:  # 매우 좋음/좋음
            multiplier += 0.5  # 50% 추가 보너스
            bonus_type = 'low_congestion'
        elif congestion_level <= 3:  # 보통
            multiplier += 0.2  # 20% 추가 보너스
            bonus_type = 'moderate_congestion'
    
    # 추천 버킷별 보너스
    bucket_bonuses = {
        'T0': 0.1,  # 아침 시간대 10% 보너스
        'T1': 0.2,  # 오전 시간대 20% 보너스
        'T2': 0.1,  # 점심 시간대 10% 보너스
        'T3': 0.2,  # 오후 시간대 20% 보너스
        'T4': 0.1,  # 저녁 시간대 10% 보너스
        'T5': 0.3,  # 밤 시간대 30% 보너스
        'T6': 0.4,  # 새벽 시간대 40% 보너스
    }
    
    bucket_bonus = bucket_bonuses.get(recommendation.recommended_bucket, 0)
    multiplier += bucket_bonus
    
    final_amount = int(base_reward * multiplier)
    
    return {
        'amount': final_amount,
        'bonus_type': bonus_type,
        'multiplier': multiplier,
        'base_reward': base_reward,
        'bucket_bonus': bucket_bonus
    }


def reward_for_trip_departure(user, trip):
    """
    AI 추천 기반 출발 시 리워드 지급
    
    Args:
        user: 사용자 객체
        trip: 시작된 여행 객체
    
    Returns:
        dict: 리워드 처리 결과
    """
    reward_info = calculate_departure_reward(trip)
    
    if reward_info['amount'] <= 0:
        return {
            'success': False,
            'message': '보상 조건을 만족하지 않습니다.',
            'reward_info': reward_info
        }
    
    # 보상 설명 생성
    bonus_descriptions = {
        'basic': '기본 출발 보상',
        'time_window': 'AI 추천 시간대 출발 보너스',
        'low_congestion': '혼잡도 낮은 시간대 출발 보너스',
        'moderate_congestion': '적정 혼잡도 시간대 출발 보너스'
    }
    
    description = f"{bonus_descriptions.get(reward_info['bonus_type'], '출발 보상')} - {trip.recommendation.origin_address} → {trip.recommendation.destination_address}"
    
    try:
        transaction_obj = create_reward_transaction(
            user=user,
            trip=trip,
            transaction_type='earn',
            amount=reward_info['amount'],
            description=description
        )
        
        return {
            'success': True,
            'transaction_id': transaction_obj.id,
            'reward_info': reward_info,
            'message': f"출발 보상 {reward_info['amount']}원이 적립되었습니다! (배율: {reward_info['multiplier']:.1f}x)"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'reward_info': reward_info
        }


def reward_for_trip_completion(user, trip, base_amount=50):
    """
    여행 완료 시 리워드 지급 (출발 보상과 별도)
    
    Args:
        user: 사용자 객체
        trip: 완료된 여행 객체
        base_amount: 기본 완료 보상 (출발 보상보다 적게)
    
    Returns:
        RewardTransaction: 생성된 리워드 거래
    """
    # 예상 시간과 실제 시간 비교 보너스
    bonus_amount = 0
    if trip.predicted_duration_min and trip.actual_duration_min:
        time_diff = abs(trip.predicted_duration_min - trip.actual_duration_min)
        if time_diff <= 5:  # 5분 이내 정확도
            bonus_amount = 30
        elif time_diff <= 10:  # 10분 이내 정확도
            bonus_amount = 15
    
    total_amount = base_amount + bonus_amount
    description = f"여행 완료 보상 - {trip.recommendation.origin_address} → {trip.recommendation.destination_address}"
    
    if bonus_amount > 0:
        description += f" (시간 예측 정확도 보너스 +{bonus_amount}원)"
    
    return create_reward_transaction(
        user=user,
        trip=trip,
        transaction_type='earn',
        amount=total_amount,
        description=description
    )
