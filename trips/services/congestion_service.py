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
    """특정 시간과 위치의 혼잡도 점수 계산 (분 단위 선형보간)"""
    congestion_data = get_optimized_congestion_data()

    weekday = target_time.strftime('%A').lower()
    hour = int(target_time.strftime('%H'))
    minute = target_time.minute

    # 기본 혼잡도 점수 (1.0~5.0)
    base_score = 2.5

    hourly_patterns = congestion_data.get("hourly_patterns", {})
    if weekday in hourly_patterns:
        daily = hourly_patterns[weekday]
        # 현재 시와 다음 시의 값을 선형 보간
        current_hour_key = f"{hour:02d}"
        next_hour_key = f"{(hour + 1) % 24:02d}"
        current_val = float(daily.get(current_hour_key, base_score))
        next_val = float(daily.get(next_hour_key, current_val))
        t = minute / 60.0
        base_score = (1 - t) * current_val + t * next_val

    # 위치별 보정 팩터 적용
    location_factors = congestion_data.get("location_factors", {})
    location_factor = float(location_factors.get(location.lower(), 1.0))

    # 주말/평일 보정
    is_weekend = target_time.weekday() >= 5
    special_events = congestion_data.get("special_events", {})

    if is_weekend:
        weekend_multiplier = float(special_events.get("weekend_multiplier", 0.8))
        base_score *= weekend_multiplier

    # 러시아워 보정 (평일 7-9시, 17-19시)
    if not is_weekend and (7 <= target_time.hour <= 9 or 17 <= target_time.hour <= 19):
        rush_multiplier = float(special_events.get("rush_hour_multiplier", 1.3))
        base_score *= rush_multiplier

    # 위치 팩터 적용
    final_score = base_score * location_factor

    return max(1.0, min(5.0, float(final_score)))


def get_optimal_time_window(current_time=None, window_hours=2, location="default", window_start_time=None, window_end_time=None):
    """
    최적의 한 시각(HH:MM)을 반환.
    - 기본: 현재 시간부터 window_hours 시간 내에서 1분 단위 스캔
    - 옵션: window_start_time, window_end_time (datetime.time) 제공 시 해당 시간창으로 스캔
    Returns:
        dict: {
          'optimal_time': {'time': 'HH:MM', 'congestion_score': float},
          'alternative_times': [{'time': 'HH:MM', 'congestion_score': float}, ...],
          'search_window': {'start': 'HH:MM', 'end': 'HH:MM'},
          'all_minutes_analyzed': int
        }
    """
    if current_time is None:
        current_time = datetime.now()

    # 검색 범위 계산
    if window_start_time and window_end_time:
        start_dt = current_time.replace(hour=window_start_time.hour, minute=window_start_time.minute, second=0, microsecond=0)
        end_dt = current_time.replace(hour=window_end_time.hour, minute=window_end_time.minute, second=0, microsecond=0)
        # 만약 종료가 시작보다 이전(자정 넘김)인 경우 다음날로 이동
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
    else:
        start_dt = current_time
        end_dt = current_time + timedelta(hours=window_hours)

    # 분 단위로 스캔
    analyzed = []
    probe = start_dt.replace(second=0, microsecond=0)
    if probe < start_dt:
        probe = probe + timedelta(minutes=1)

    while probe < end_dt:
        score = calculate_congestion_score(probe, location)
        analyzed.append({'time': probe, 'score': round(score, 4)})
        probe = probe + timedelta(minutes=1)

    if not analyzed:
        return None

    # 정밀화: 5분 이동평균 + 기울기 패널티 적용한 결합 점수로 최소치 탐색
    window_half = 2  # 총 5분 창
    slope_lambda = 0.2
    combined = []
    for idx, entry in enumerate(analyzed):
        start = max(0, idx - window_half)
        end = min(len(analyzed), idx + window_half + 1)
        # 이동 평균
        avg = sum(m['score'] for m in analyzed[start:end]) / (end - start)
        # 기울기(변화율) 패널티
        prev_score = analyzed[idx-1]['score'] if idx > 0 else analyzed[idx]['score']
        slope = abs(entry['score'] - prev_score)
        combined_score = round(avg + slope_lambda * slope, 4)
        combined.append({'time': entry['time'], 'score': combined_score})

    # 최소값과 대안 선택(최소 간격 10분)
    min_gap = 10
    combined_sorted = sorted(combined, key=lambda x: x['score'])
    selected = []
    for cand in combined_sorted:
        if not selected:
            selected.append(cand)
        else:
            too_close = any(abs(int((cand['time'] - s['time']).total_seconds() // 60)) < min_gap for s in selected)
            if not too_close:
                selected.append(cand)
        if len(selected) >= 3:
            break

    best = selected[0]
    alternatives = selected[1:3]

    return {
        'optimal_time': {
            'time': best['time'].strftime('%H:%M'),
            'congestion_score': round(best['score'], 2)
        },
        'alternative_times': [
            {
                'time': alt['time'].strftime('%H:%M'),
                'congestion_score': round(alt['score'], 2)
            } for alt in alternatives
        ],
        'search_window': {
            'start': start_dt.strftime('%H:%M'),
            'end': end_dt.strftime('%H:%M')
        },
        'all_minutes_analyzed': len(analyzed)
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


def get_precise_departure_time(bucket_code, date_ref=None, location="default"):
    """
    특정 버킷(T0~T3) 범위 내에서 '정확한 분'으로 최적 출발 시각 추천
    """
    if date_ref is None:
        date_ref = datetime.now()

    bucket_times = {
        'T0': {'start': 6, 'end': 8},
        'T1': {'start': 8, 'end': 10},
        'T2': {'start': 17, 'end': 19},
        'T3': {'start': 19, 'end': 21},
    }

    if bucket_code not in bucket_times:
        return None

    start_hour = bucket_times[bucket_code]['start']
    end_hour = bucket_times[bucket_code]['end']

    best_time = None
    best_score = float('inf')

    # 버킷 범위 내 모든 분 탐색
    cursor = date_ref.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end_dt = date_ref.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    while cursor < end_dt:
        score = calculate_congestion_score(cursor, location)
        if score < best_score:
            best_score = score
            best_time = cursor
        cursor = cursor + timedelta(minutes=1)

    if not best_time:
        return None

    return {
        'optimal_departure': best_time.strftime('%H:%M'),
        'congestion_score': round(float(best_score), 2),
        'bucket': bucket_code,
        'time_window': {
            'start': f"{start_hour:02d}:00",
            'end': f"{end_hour:02d}:00"
        },
        'rationale': f"{bucket_code} 범위 내에서 혼잡도가 가장 낮은 분({best_time.strftime('%H:%M')})을 추천합니다."
    }
