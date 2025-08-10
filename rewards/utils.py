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


# def calculate_departure_reward(trip):
#     """
#     AI 추천 기반 출발 시간 보상 계산 (현재 비활성화)
#     - AI가 추천한 정확한 시간에 출발해야 보상
#     
#     Args:
#         trip: 여행 객체
#     
#     Returns:
#         dict: 보상 정보 {'amount': int, 'bonus_type': str, 'multiplier': float}
#     """
#     if not trip.recommendation or not trip.started_at:
#         return {'amount': 0, 'bonus_type': 'none', 'multiplier': 1.0}
#     
#     base_reward = 100
#     multiplier = 1.0
#     bonus_type = 'basic'
#     
#     # 추천 시간 윈도우 체크
#     recommendation = trip.recommendation
#     departure_time = trip.started_at.time()
#     
#     # AI가 추천한 정확한 시간에 출발했는지 체크 (5분 허용 오차)
#     recommended_start = recommendation.window_start
#     recommended_end = recommendation.window_end
#     
#     # 정확한 시간 출발 보너스 (5분 이내)
#     time_diff_minutes = abs((departure_time.hour * 60 + departure_time.minute) - 
#                            (recommended_start.hour * 60 + recommended_start.minute))
#     
#     if time_diff_minutes <= 5:  # 5분 이내 출발
#         multiplier += 0.5  # 50% 보너스
#         bonus_type = 'exact_time'
#     elif recommendation.window_start <= departure_time <= recommendation.window_end:
#         multiplier += 0.2  # 20% 보너스 (윈도우 내 출발)
#         bonus_type = 'time_window'
#     
#     # 혼잡도 기반 보너스
#     congestion_level = recommendation.expected_congestion_level
#     if congestion_level:
#         if congestion_level <= 2:  # 매우 좋음/좋음
#             multiplier += 0.3  # 30% 추가 보너스
#             bonus_type = 'low_congestion'
#         elif congestion_level <= 3: # 보통
#             multiplier += 0.1  # 10% 추가 보너스
#             bonus_type = 'moderate_congestion'
#     
#     # 추천 버킷별 보너스
#     bucket_bonuses = {
#         'T0': 0.1,  # 아침 시간대 10% 보너스
#         'T1': 0.2,  # 오전 시간대 20% 보너스
#         'T2': 0.1,  # 점심 시간대 10% 보너스
#         'T3': 0.0,  # 오후 시간대 보너스 없음
#         'T4': 0.1,  # 저녁 시간대 10% 보너스
#         'T5': 0.2,  # 밤 시간대 20% 보너스
#         'T6': 0.1   # 새벽 시간대 10% 보너스
#     }
#     
#     bucket = recommendation.recommended_bucket
#     if bucket in bucket_bonuses:
#         multiplier += bucket_bonuses[bucket]
#         bonus_type = 'time_bucket'
#     
#     final_amount = int(base_reward * multiplier)
#     
#     return {
#         'amount': final_amount,
#         'bonus_type': bonus_type,
#         'multiplier': round(multiplier, 2)
#     }


def calculate_arrival_reward(trip):
    """
    AI 추천 기반 도착 시간 보상 계산
    - AI가 예상한 시간에 도착해야 보상
    
    Args:
        trip: 여행 객체
    
    Returns:
        dict: 보상 정보 {'amount': int, 'bonus_type': str, 'multiplier': float}
    """
    if not trip.recommendation or not trip.arrived_at or not trip.started_at:
        return {'amount': 0, 'bonus_type': 'none', 'multiplier': 1.0}
    
    base_reward = 50
    multiplier = 1.0
    bonus_type = 'basic'
    
    # AI가 예상한 소요 시간과 실제 소요 시간 비교
    expected_duration = trip.recommendation.expected_duration_min
    actual_duration = (trip.arrived_at - trip.started_at).total_seconds() / 60
    
    # 예상 시간과의 차이 (10분 허용 오차)
    time_diff = abs(actual_duration - expected_duration)
    
    if time_diff <= 5:  # 5분 이내 도착
        multiplier += 0.4  # 40% 보너스
        bonus_type = 'exact_time'
    elif time_diff <= 10:  # 10분 이내 도착
        multiplier += 0.2  # 20% 보너스
        bonus_type = 'close_time'
    
    # 혼잡도 기반 보너스
    congestion_level = trip.recommendation.expected_congestion_level
    if congestion_level:
        if congestion_level <= 2:  # 매우 좋음/좋음
            multiplier += 0.2  # 20% 추가 보너스
            bonus_type = 'low_congestion'
    
    final_amount = int(base_reward * multiplier)
    
    return {
        'amount': final_amount,
        'bonus_type': bonus_type,
        'multiplier': round(multiplier, 2)
    }


# def reward_for_trip_departure(user, trip):
#     """
#     AI 추천 기반 출발 시 리워드 지급 (현재 비활성화)
#     
#     Args:
#         user: 사용자 객체
#         trip: 시작된 여행 객체
#     
#     Returns:
#         dict: 리워드 처리 결과
#     """
#     reward_info = calculate_departure_reward(trip)
#     
#     if reward_info['amount'] <= 0:
#         return {
#             'success': False,
#             'message': '보상 조건을 만족하지 않습니다.',
#             'reward_info': reward_info
#         }
#     
#     # 보상 설명 생성
#     bonus_descriptions = {
#         'basic': '기본 출발 보상',
#         'exact_time': 'AI 추천 정확 시간 출발 보너스',
#         'time_window': 'AI 추천 시간대 출발 보너스',
#         'low_congestion': '혼잡도 낮은 시간대 출발 보너스',
#         'moderate_congestion': '적정 혼잡도 시간대 출발 보너스'
#     }
#     
#     description = f"{bonus_descriptions.get(reward_info['bonus_type'], '출발 보상')} - {trip.recommendation.origin_address} → {trip.recommendation.daily_destination_address}"
#     
#     try:
#         transaction_obj = create_reward_transaction(
#             user=user,
#             trip=trip,
#             transaction_type='earn',
#             amount=reward_info['amount'],
#             description=description
#         )
#         
#         return {
#             'success': True,
#             'transaction_id': transaction_obj.id,
#             'reward_info': reward_info,
#             'message': f"출발 보상 {reward_info['amount']}원이 적립되었습니다! (배율: {reward_info['multiplier']:.1f}x)"
#         }
#     except Exception as e:
#         return {
#             'success': False,
#             'error': str(e),
#             'reward_info': reward_info
#         }


def reward_for_trip_completion(user, trip, base_amount=50):
    """
    여행 완료 시 리워드 지급 (AI 추천 기반 도착 보상)
    
    Args:
        user: 사용자 객체
        trip: 완료된 여행 객체
        base_amount: 기본 완료 보상
    
    Returns:
        dict: 리워드 처리 결과
    """
    # AI 추천 기반 도착 보상 계산
    arrival_reward_info = calculate_arrival_reward(trip)

    # 잔액 정보를 포함시키기 위해 지갑 준비
    wallet, _ = Wallet.objects.get_or_create(user=user)

    if arrival_reward_info['amount'] <= 0:
        return {
            'success': False,
            'message': '도착 보상 조건을 만족하지 않습니다.',
            'reward_info': arrival_reward_info,
            'completion_reward': {
                'total_reward': 0,
                'base_reward': base_amount,
                'multiplier': 1.0,
            },
            'wallet_balance': wallet.balance,
        }
    
    # 보상 설명 생성
    bonus_descriptions = {
        'basic': '기본 도착 보상',
        'exact_time': 'AI 예상 시간 정확 도착 보너스',
        'close_time': 'AI 예상 시간 근접 도착 보너스',
        'low_congestion': '혼잡도 낮은 시간대 도착 보너스'
    }
    
    description = f"{bonus_descriptions.get(arrival_reward_info['bonus_type'], '도착 보상')} - {trip.recommendation.origin_address} → {trip.recommendation.destination_address}"
    
    try:
        transaction_obj = create_reward_transaction(
            user=user,
            trip=trip,
            transaction_type='earn',
            amount=arrival_reward_info['amount'],
            description=description
        )

        # 최신 잔액 반영
        wallet.refresh_from_db()

        return {
            'success': True,
            'transaction_id': transaction_obj.id,
            'reward_info': arrival_reward_info,
            'completion_reward': {
                'total_reward': arrival_reward_info['amount'],
                'base_reward': base_amount,
                'multiplier': arrival_reward_info['multiplier'],
            },
            'wallet_balance': wallet.balance,
            'message': f"도착 보상 {arrival_reward_info['amount']}원이 적립되었습니다! (배율: {arrival_reward_info['multiplier']:.1f}x)"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'reward_info': arrival_reward_info,
            'completion_reward': {
                'total_reward': 0,
                'base_reward': base_amount,
                'multiplier': 1.0,
            },
            'wallet_balance': wallet.balance,
        }
