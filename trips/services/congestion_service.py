import json
import os
from datetime import datetime, timedelta, time
from django.conf import settings


def get_monthly_index():
    """기존 월별 혼잡도 데이터를 불러오는 함수"""
    json_path = os.path.join(settings.BASE_DIR, 'trips', 'fixtures', 'congestion_index.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get('congestion_index', {})
    except FileNotFoundError:
        return {}


def get_optimized_congestion_data():
    """최적화된 시간별 혼잡도 데이터를 불러오는 함수"""
    json_path = os.path.join(settings.BASE_DIR, 'trips', 'fixtures', 'congestion_optimized.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {
            "monthly_congestion": {},
            "hourly_patterns": {},
            "special_events": {},
            "location_factors": {}
        }


def calculate_congestion_score(target_time, location="default"):
    """특정 시간과 위치의 혼잡도 점수 계산"""
    congestion_data = get_optimized_congestion_data()
    
    # 요일별 시간별 혼잡도 패턴
    weekday = target_time.strftime('%A').lower()
    hour = target_time.strftime('%H')
    
    # 기본 혼잡도 점수 (1.0~5.0)
    base_score = 2.5
    
    # 요일별 시간별 패턴이 있으면 사용
    if weekday in congestion_data.get("hourly_patterns", {}):
        hourly_data = congestion_data["hourly_patterns"][weekday]
        base_score = hourly_data.get(hour, base_score)
    
    # 위치별 보정 팩터 적용
    location_factors = congestion_data.get("location_factors", {})
    location_factor = location_factors.get(location.lower(), 1.0)
    
    # 주말/평일 보정
    is_weekend = target_time.weekday() >= 5
    special_events = congestion_data.get("special_events", {})
    
    if is_weekend:
        weekend_multiplier = special_events.get("weekend_multiplier", 0.8)
        base_score *= weekend_multiplier
    
    # 러시아워 보정 (평일 7-9시, 17-19시)
    if not is_weekend and (7 <= target_time.hour <= 9 or 17 <= target_time.hour <= 19):
        rush_multiplier = special_events.get("rush_hour_multiplier", 1.3)
        base_score *= rush_multiplier
    
    # 위치 팩터 적용
    final_score = base_score * location_factor
    
    # 점수를 1.0~5.0 범위로 제한
    return max(1.0, min(5.0, final_score))


def get_optimal_time_window(current_time=None, window_hours=2, location="default"):
    """
    현재 시간으로부터 지정된 시간 내에서 최적의 여행 시간 추천
    
    Args:
        current_time: 기준 시간 (None이면 현재 시간)
        window_hours: 검색할 시간 범위 (기본 2시간)
        location: 목적지 위치 (혼잡도 보정용)
    
    Returns:
        dict: 최적 시간대 정보
    """
    if current_time is None:
        current_time = datetime.now()
    
    # 검색 범위 설정
    end_time = current_time + timedelta(hours=window_hours)
    
    # 30분 단위로 시간 슬롯 생성
    time_slots = []
    slot_time = current_time
    
    while slot_time < end_time:
        slot_end = slot_time + timedelta(minutes=30)
        if slot_end > end_time:
            slot_end = end_time
        
        # 각 슬롯의 혼잡도 계산
        congestion_score = calculate_congestion_score(slot_time, location)
        
        # 시간대 버킷 정보
        bucket_info = get_time_bucket_info(slot_time)
        
        time_slots.append({
            'slot_start': slot_time,
            'slot_end': slot_end,
            'duration_minutes': int((slot_end - slot_time).total_seconds() / 60),
            'congestion_score': congestion_score,
            'bucket_code': bucket_info['code'],
            'bucket_name': bucket_info['name'],
            'recommendation_level': get_recommendation_level(congestion_score)
        })
        
        slot_time += timedelta(minutes=30)
    
    if not time_slots:
        return {
            'optimal_window': None,
            'alternatives': [],
            'recommendation_reason': '검색 가능한 시간대가 없습니다.'
        }
    
    # 혼잡도가 가장 낮은 슬롯 선택
    optimal_slot = min(time_slots, key=lambda x: x['congestion_score'])
    
    # 대안 제시 (혼잡도 낮은 순으로 2개)
    alternatives = sorted([slot for slot in time_slots if slot != optimal_slot], 
                         key=lambda x: x['congestion_score'])[:2]
    
    return {
        'optimal_window': optimal_slot,
        'alternatives': alternatives,
        'recommendation_reason': generate_recommendation_reason(optimal_slot, current_time),
        'search_parameters': {
            'search_start': current_time.strftime('%Y-%m-%d %H:%M'),
            'search_end': end_time.strftime('%Y-%m-%d %H:%M'),
            'location': location,
            'total_slots_analyzed': len(time_slots)
        }
    }


def get_time_bucket_info(target_time):
    """시간을 기준으로 해당 시간대 버킷 정보 반환"""
    time_buckets = settings.CONGESTION_BUCKETS
    target_hour_minute = target_time.strftime('%H:%M')
    
    for bucket_code, bucket_info in time_buckets.items():
        start_time = bucket_info['start']
        end_time = bucket_info['end']
        
        # 24시간 넘어가는 경우 처리
        if start_time > end_time:  # 예: 23:00 - 05:59
            if target_hour_minute >= start_time or target_hour_minute <= end_time:
                return {'code': bucket_code, 'name': bucket_info['name']}
        else:  # 일반적인 경우
            if start_time <= target_hour_minute <= end_time:
                return {'code': bucket_code, 'name': bucket_info['name']}
    
    return {'code': 'unknown', 'name': '기타 시간대'}


def get_recommendation_level(congestion_score):
    """혼잡도 점수를 기반으로 추천 레벨 반환"""
    if congestion_score <= 2.0:
        return "매우 좋음"
    elif congestion_score <= 2.5:
        return "좋음"
    elif congestion_score <= 3.5:
        return "보통"
    elif congestion_score <= 4.0:
        return "혼잡"
    else:
        return "매우 혼잡"


def generate_recommendation_reason(optimal_slot, current_time):
    """추천 이유 생성"""
    time_diff = optimal_slot['slot_start'] - current_time
    minutes_until = int(time_diff.total_seconds() / 60)
    
    if minutes_until <= 5:
        timing = "지금 바로"
    elif minutes_until <= 30:
        timing = f"{minutes_until}분 후"
    else:
        hours = minutes_until // 60
        remaining_minutes = minutes_until % 60
        timing = f"{hours}시간 {remaining_minutes}분 후"
    
    level = optimal_slot['recommendation_level']
    bucket_name = optimal_slot['bucket_name']
    
    return f"{timing} 출발하는 {bucket_name}이 가장 적합합니다. 예상 혼잡도: {level}"


def get_monthly_index(target_dt=None, region_code=None, version='v1'):
    """
    지정된 월의 혼잡도 인덱스 조회
    JSON 파일에서 직접 읽어옴
    target_dt가 None이면 현재 월 사용
    """
    if target_dt is None:
        target_dt = datetime.now()
    
    target_month = target_dt.strftime('%Y%m')
    
    # JSON 파일 경로 설정
    json_file_path = os.path.join(settings.BASE_DIR, 'trips', 'fixtures', 'congestion_data.json')
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            congestion_data = json.load(f)
        
        # 해당 월 데이터 조회
        if target_month in congestion_data:
            monthly_data = congestion_data[target_month]
            return {
                'T0': float(monthly_data.get('T0', 1.0)),
                'T1': float(monthly_data.get('T1', 2.5)),
                'T2': float(monthly_data.get('T2', 3.0)),
                'T3': float(monthly_data.get('T3', 2.0)),
            }
        else:
            # 해당 월 데이터가 없으면 가장 최근 데이터 사용
            if congestion_data:
                # 월 키를 정렬해서 가장 최근 데이터 가져오기
                latest_month = max(congestion_data.keys())
                latest_data = congestion_data[latest_month]
                return {
                    'T0': float(latest_data.get('T0', 1.0)),
                    'T1': float(latest_data.get('T1', 2.5)),
                    'T2': float(latest_data.get('T2', 3.0)),
                    'T3': float(latest_data.get('T3', 2.0)),
                }
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    
    # 파일을 읽을 수 없거나 데이터가 없으면 기본값 반환
    return {
        'T0': 1.0,
        'T1': 2.5,
        'T2': 3.0,
        'T3': 2.0,
    }


def expand_bucket_to_candidates(date_ref, bucket_code):
    """
    bucket_code를 실제 시간대로 확장
    settings.CONGESTION_BUCKETS 사용
    """
    if not hasattr(settings, 'CONGESTION_BUCKETS'):
        # 기본값 설정
        buckets = {
            'T0': {'start': '06:00', 'end': '08:00'},
            'T1': {'start': '08:00', 'end': '10:00'},
            'T2': {'start': '17:00', 'end': '19:00'},
            'T3': {'start': '19:00', 'end': '21:00'},
        }
    else:
        buckets = settings.CONGESTION_BUCKETS
    
    if bucket_code not in buckets:
        raise ValueError(f"Invalid bucket code: {bucket_code}")
    
    bucket_info = buckets[bucket_code]
    start_time = bucket_info['start']
    end_time = bucket_info['end']
    
    # date_ref와 시간을 조합하여 datetime 객체 생성
    start_dt = datetime.combine(date_ref.date(), datetime.strptime(start_time, '%H:%M').time())
    end_dt = datetime.combine(date_ref.date(), datetime.strptime(end_time, '%H:%M').time())
    
    return start_dt, end_dt
