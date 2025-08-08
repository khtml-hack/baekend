import json
import os
from datetime import datetime, time
from django.conf import settings
from ..models import Recommendation
from .congestion_service import get_monthly_index
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
    여행 추천 생성
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
    
    # 5. settings에서 시간 정보 가져오기
    bucket_info = settings.CONGESTION_BUCKETS.get(
        ai_recommendation.get('recommended_bucket', best_bucket),
        settings.CONGESTION_BUCKETS['T0']
    )
    
    # 6. Recommendation 객체 생성
    recommendation = Recommendation.objects.create(
        user=user,
        origin_address=normalized_origin,
        destination_address=normalized_destination,
        recommended_bucket=ai_recommendation.get('recommended_bucket', best_bucket),
        window_start=time.fromisoformat(
            ai_recommendation.get('recommended_window', {}).get('start', bucket_info['start'])
        ),
        window_end=time.fromisoformat(
            ai_recommendation.get('recommended_window', {}).get('end', bucket_info['end'])
        ),
        expected_duration_min=ai_recommendation.get('expected_duration_min'),
        expected_congestion_level=ai_recommendation.get('expected_congestion_level'),
        rationale=ai_recommendation.get('rationale', '혼잡도 데이터를 기반으로 한 추천입니다.')
    )
    
    # 7. 결과 반환
    result = {
        'recommendation_id': recommendation.id,
        'recommended_bucket': recommendation.recommended_bucket,
        'recommended_window': {
            'start': recommendation.window_start.strftime('%H:%M'),
            'end': recommendation.window_end.strftime('%H:%M')
        },
        'rationale': recommendation.rationale,
        'expected_duration_min': recommendation.expected_duration_min,
        'expected_congestion_level': recommendation.expected_congestion_level,
        'origin_address': normalized_origin,
        'destination_address': normalized_destination
    }
    
    return result
