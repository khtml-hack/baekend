import json
import os
from datetime import datetime, time, timedelta
from django.conf import settings
from ..models import Recommendation
from .congestion_service import (
    get_monthly_index,
    get_optimal_time_window,
    calculate_congestion_score,
    get_recommendation_level,
)
from integrations.kakao import search_address


def _infer_location_from_address(address: str) -> str:
    """간단한 문자열 매핑으로 혼잡도 위치 키를 유추 (없으면 default)."""
    if not address:
        return "default"
    lower = address.lower()
    # 한글 키워드도 함께 검사
    if "gangnam" in lower or "강남" in address:
        return "gangnam"
    if "hongdae" in lower or "홍대" in address:
        return "hongdae"
    if "myeongdong" in lower or "명동" in address:
        return "myeongdong"
    return "default"
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
    여행 추천 생성 (2개의 추천 옵션 제공)
    - 각 옵션별로 정밀한 분 단위 시간 추천
    - 최종 optimal_departure_time은 분 단위 결정론 스캐닝으로 확정
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
    
    # 5. OpenAI를 통한 추천 생성 (2개 옵션)
    ai_recommendation = get_travel_recommendation(
        normalized_origin, 
        normalized_destination, 
        current_congestion,
        full_congestion_data
    )
    
    # 6. AI 추천에서 2개 옵션 처리
    recommendations = ai_recommendation.get('recommendations', [])
    # AI가 제공한 current_time_analysis는 무시하고, 서버 현재 시각 기준으로 항상 재계산
    # 목적지 주소로부터 간단히 위치 키 추정
    inferred_location = _infer_location_from_address(normalized_destination)
    
    if len(recommendations) < 2:
        # 기본값으로 2개 옵션 생성
        recommendations = [
            {
                "option_type": "최적 시간",
                "recommended_bucket": best_bucket,
                "recommended_window": {"start": "06:00", "end": "08:00"},
                "optimal_departure_time": "06:30",
                "rationale": "혼잡도 데이터를 기반으로 한 기본 추천입니다.",
                "expected_duration_min": 30,
                "expected_congestion_level": 2,
                "congestion_description": "원활",
                "time_sensitivity": "보통",
                "time_saved_min": 20,
                "reward_amount": 100
            },
            {
                "option_type": "대안 시간",
                "recommended_bucket": "T1",
                "recommended_window": {"start": "08:00", "end": "10:00"},
                "optimal_departure_time": "08:30",
                "rationale": "T1 시간대도 비교적 혼잡도가 낮습니다.",
                "expected_duration_min": 35,
                "expected_congestion_level": 3,
                "congestion_description": "보통",
                "time_sensitivity": "보통",
                "time_saved_min": 15,
                "reward_amount": 80
            }
        ]
    
    # 7. 각 옵션별로 분 단위 결정론 스캔으로 최적 분 확정
    processed_recommendations = []
    
    for i, rec in enumerate(recommendations):
        window_start_str = rec.get('recommended_window', {}).get('start', '06:00')
        window_end_str = rec.get('recommended_window', {}).get('end', '08:00')
        window_start = time.fromisoformat(window_start_str)
        window_end = time.fromisoformat(window_end_str)
        
        # 분 단위 결정론 스캔으로 최적 분 확정
        deterministic = get_optimal_time_window(
            current_time=datetime.now(),
            window_hours=None,
            location='default',
            window_start_time=window_start,
            window_end_time=window_end
        )
        
        optimal_departure = deterministic['optimal_time']['time'] if deterministic else rec.get('optimal_departure_time', window_start_str)
        
        processed_recommendations.append({
            'option_type': rec.get('option_type', f'옵션 {i+1}'),
            'recommended_bucket': rec.get('recommended_bucket', best_bucket),
            'recommended_window': {
                'start': window_start.strftime('%H:%M'),
                'end': window_end.strftime('%H:%M')
            },
            'optimal_departure_time': optimal_departure,
            'rationale': rec.get('rationale', '혼잡도 데이터를 기반으로 한 추천입니다.'),
            'expected_duration_min': rec.get('expected_duration_min', 30),
            'expected_congestion_level': rec.get('expected_congestion_level', 3),
            'congestion_description': rec.get('congestion_description', '보통'),
            'time_sensitivity': rec.get('time_sensitivity', '보통'),
            'time_saved_min': rec.get('time_saved_min', 0),
            'reward_amount': rec.get('reward_amount', 50)
        })
    
    # 8. Recommendation 객체 생성 (첫 번째 옵션을 메인으로 저장)
    main_rec = processed_recommendations[0]
    recommendation = Recommendation.objects.create(
        user=user,
        origin_address=normalized_origin,
        destination_address=normalized_destination,
        recommended_bucket=main_rec['recommended_bucket'],
        window_start=time.fromisoformat(main_rec['recommended_window']['start']),
        window_end=time.fromisoformat(main_rec['recommended_window']['end']),
        expected_duration_min=main_rec['expected_duration_min'],
        expected_congestion_level=main_rec['expected_congestion_level'],
        rationale=main_rec['rationale']
    )
    
    # 9. 현재 시간 분석이 비어 있으면 서버에서 결정론적으로 채움
    now_dt = datetime.now()
    try:
        duration_min = int(main_rec.get('expected_duration_min') or 30)
    except Exception:
        duration_min = 30
    score = calculate_congestion_score(now_dt, location=inferred_location)
    current_analysis = {
        'departure_time': now_dt.strftime('%H:%M'),
        'arrival_time': (now_dt + timedelta(minutes=duration_min)).strftime('%H:%M'),
        'duration_min': duration_min,
        'congestion_level': round(float(score), 2),
        'congestion_description': get_recommendation_level(score),
        'location': inferred_location,
    }

    # 10. 결과 반환 (2개 옵션 모두 포함)
    result = {
        'recommendation_id': recommendation.id,
        'recommendations': processed_recommendations,
        'current_time_analysis': current_analysis,
        'origin_address': normalized_origin,
        'destination_address': normalized_destination,
        'ai_confidence': 'high'
    }
    
    return result
