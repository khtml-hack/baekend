import json
import os
from datetime import datetime, time
from django.conf import settings
from ..models import Recommendation
from .congestion_service import get_monthly_index, get_optimal_time_window
from integrations.kakao import search_address
from integrations.openai_gpt import get_travel_recommendation


def get_congestion_json_data():
    """
    혼잡도 JSON 데이터를 직접 읽어서 반환
    """
    json_file_path = os.path.join(settings.BASE_DIR, 'trips', 'fixtures', 'congestion_data.json')
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def create_recommendation(user, origin_address, destination_address, region_code=None):
    """
    여행 추천 생성 (정밀한 분 단위 시간 추천)
    - 최종 optimal_departure_time은 분 단위 결정론 스캐닝(get_optimal_time_window)으로 확정해
      optimal-time API와 동일하게 맞춘다.
    """
    # 1. Kakao API를 통한 주소 정규화
    origin_info = search_address(origin_address)
    destination_info = search_address(destination_address)
    
    normalized_origin = origin_info.get('normalized_address', origin_address)
    normalized_destination = destination_info.get('normalized_address', destination_address)
    
    # 2. 혼잡도 데이터 조회 (현재 월)
    current_congestion = get_monthly_index(region_code=region_code)
    
    # 3. 전체 혼잡도 JSON 데이터 조회 (AI가 패턴 분석용)
    full_congestion_data = get_congestion_json_data()
    
    # 4. 최적 bucket 선택 (혼잡도가 가장 낮은 시간대)
    best_bucket = min(current_congestion.items(), key=lambda x: x[1])[0]
    
    # 5. OpenAI를 통한 추천 생성 (전체 데이터와 현재 월 데이터 모두 제공)
    ai_recommendation = get_travel_recommendation(
        normalized_origin, 
        normalized_destination, 
        current_congestion,
        full_congestion_data  # 전체 데이터 추가
    )
    
    # 6. AI 추천에서 시간 정보 추출 (윈도우가 없으면 버킷 기본값으로 대체 가능하지만, 여기서는 필수로 가정)
    recommended_bucket = ai_recommendation.get('recommended_bucket', best_bucket)
    window_start_str = ai_recommendation.get('recommended_window', {}).get('start', '06:00')
    window_end_str = ai_recommendation.get('recommended_window', {}).get('end', '08:00')
    window_start = time.fromisoformat(window_start_str)
    window_end = time.fromisoformat(window_end_str)

    # 7. 분 단위 결정론 스캔으로 최적 분 확정 (optimal-time API와 동일 로직)
    # location은 경량 키워드이므로 일단 default를 사용. 필요시 주소에서 지역 키워드 추출로 확장 가능.
    deterministic = get_optimal_time_window(
        current_time=datetime.now(),
        window_hours=None,  # 사용 안 함
        location='default',
        window_start_time=window_start,
        window_end_time=window_end
    )
    optimal_departure = deterministic['optimal_time']['time'] if deterministic else ai_recommendation.get('optimal_departure_time', window_start_str)
    alternative_times = [alt['time'] for alt in (deterministic.get('alternative_times', []) if deterministic else [])]
    
    # 8. Recommendation 객체 생성
    recommendation = Recommendation.objects.create(
        user=user,
        origin_address=normalized_origin,
        destination_address=normalized_destination,
        recommended_bucket=recommended_bucket,
        window_start=window_start,
        window_end=window_end,
        expected_duration_min=ai_recommendation.get('expected_duration_min'),
        expected_congestion_level=ai_recommendation.get('expected_congestion_level'),
        rationale=ai_recommendation.get('rationale', '혼잡도 데이터를 기반으로 한 추천입니다.')
    )
    
    # 9. 결과 반환 (결정론 결과로 통일)
    result = {
        'recommendation_id': recommendation.id,
        'recommended_bucket': recommendation.recommended_bucket,
        'recommended_window': {
            'start': recommendation.window_start.strftime('%H:%M'),
            'end': recommendation.window_end.strftime('%H:%M')
        },
        'optimal_departure_time': optimal_departure,
        'rationale': recommendation.rationale,
        'expected_duration_min': recommendation.expected_duration_min,
        'expected_congestion_level': recommendation.expected_congestion_level,
        'time_sensitivity': ai_recommendation.get('time_sensitivity', '보통'),
        'alternative_times': alternative_times,
        'origin_address': normalized_origin,
        'destination_address': normalized_destination,
        'ai_confidence': 'high'
    }
    
    return result
