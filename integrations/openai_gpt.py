"""
OpenAI GPT Integration Module
"""
import json
from openai import OpenAI
from django.conf import settings


def chat_json(system, user, model="gpt-4o-mini", temperature=0.2):
    """
    OpenAI GPT 채팅 API (JSON 응답)
    
    Args:
        system (str): 시스템 메시지
        user (str): 사용자 메시지
        model (str): 사용할 모델 (기본값: gpt-4o-mini)
        temperature (float): 온도 설정 (기본값: 0.2)
        
    Returns:
        str: JSON 문자열 응답
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=temperature
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API 호출 실패: {str(e)}")


def _extract_json(text: str):
    """Best-effort JSON extraction from model output."""
    try:
        return json.loads(text)
    except Exception:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
        raise


def get_travel_recommendation(origin_address, destination_address, current_congestion, full_congestion_data=None, tmap_summary=None):
    """
    OpenAI GPT를 사용하여 여행 추천 정보 생성
    current_congestion: 현재 월의 혼잡도 데이터
    full_congestion_data: 전체 월별 혼잡도 데이터 (패턴 분석용)
    tmap_summary: TMAP 요약(선택)
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API Key가 설정되지 않았습니다.")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # 현재 월 혼잡도 데이터를 문자열로 변환
    current_congestion_str = ", ".join([f"{k}: {v}" for k, v in current_congestion.items()])
    
    # 전체 데이터가 있으면 패턴 분석 정보 추가
    pattern_info = ""
    if full_congestion_data:
        # 시간대별 평균 계산
        time_averages = {'T0': 0, 'T1': 0, 'T2': 0, 'T3': 0}
        month_count = len(full_congestion_data)
        
        for month_data in full_congestion_data.values():
            for time_slot in ['T0', 'T1', 'T2', 'T3']:
                if time_slot in month_data:
                    time_averages[time_slot] += month_data[time_slot]
        
        for time_slot in time_averages:
            time_averages[time_slot] = round(time_averages[time_slot] / month_count, 2)
        
        pattern_info = f"\n전체 기간 평균 혼잡도: {', '.join([f'{k}: {v}' for k, v in time_averages.items()])}"

    # v2 prompt: UI 친화 JSON, 버킷 제거, 선택적 TMAP 요약 반영
    tmap_text = ""
    if tmap_summary:
        counts = tmap_summary.get('counts', {})
        critical = ", ".join(tmap_summary.get('critical_roads', []))
        tmap_text = f"\n출발지 주변 실시간 교통 요약(TMAP): 총 {tmap_summary.get('total_roads', 0)}개 구간, 원활 {counts.get('0',0)}, 서행 {counts.get('1',0)}, 지체 {counts.get('2',0)}, 정체 {counts.get('3',0)+counts.get('4',0)}. 주요 정체: {critical}"

    prompt = f"""
    당신은 교통 혼잡도 전문가입니다. 아래 데이터를 사용해 분 단위로 출발 시간을 2개 제안하세요.

    출발지: {origin_address}
    목적지: {destination_address}
    현재 월 혼잡도 지표: {current_congestion_str}{pattern_info}{tmap_text}

    - 시간대 라벨(T0/T1 등) 금지, 실제 시간(HH:MM)만 사용
    - 각 옵션의 추천 윈도우는 2시간 이하
    - 첫 번째는 최적, 두 번째는 대안

    아래 JSON만 반환:
    {{
      "current": {{
        "departure_time": "HH:MM",
        "arrival_time": "HH:MM",
        "duration_min": int,
        "congestion_level": 1-5,
        "congestion_description": "매우 혼잡/혼잡/보통/원활/매우 원활"
      }},
      "options": [
        {{
          "title": "최적 시간",
          "depart_in_text": "예: 1시간 뒤 출발 (10:41)",
          "window": {{"start": "HH:MM", "end": "HH:MM"}},
          "optimal_departure_time": "HH:MM",
          "expected_duration_min": int,
          "congestion_level": 1-5,
          "congestion_description": "원활/보통/혼잡",
          "time_saved_min": int,
          "reward_amount": int
        }},
        {{
          "title": "대안 시간",
          "depart_in_text": "예: 45분 뒤 출발 (10:26)",
          "window": {{"start": "HH:MM", "end": "HH:MM"}},
          "optimal_departure_time": "HH:MM",
          "expected_duration_min": int,
          "congestion_level": 1-5,
          "congestion_description": "원활/보통/혼잡",
          "time_saved_min": int,
          "reward_amount": int
        }}
      ]
    }}

    JSON 이외의 텍스트는 출력하지 마세요.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 교통 혼잡도 전문가이며, 반드시 UI 친화적 JSON만 반환합니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700,
            temperature=0.2
        )
        
        content = response.choices[0].message.content.strip()
        return _extract_json(content)
        
    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}")
        # 기본값 반환 (UI 스키마)
        return {
            "current": {
                "departure_time": "09:41",
                "arrival_time": "10:31",
                "duration_min": 50,
                "congestion_level": 5,
                "congestion_description": "매우 혼잡"
            },
            "options": [
                {
                    "title": "최적 시간",
                    "depart_in_text": "1시간 뒤 출발 (10:41)",
                    "window": {"start": "10:00", "end": "12:00"},
                    "optimal_departure_time": "10:41",
                    "expected_duration_min": 30,
                    "congestion_level": 2,
                    "congestion_description": "원활",
                    "time_saved_min": 20,
                    "reward_amount": 100
                },
                {
                    "title": "대안 시간",
                    "depart_in_text": "45분 뒤 출발 (10:26)",
                    "window": {"start": "10:00", "end": "12:00"},
                    "optimal_departure_time": "10:26",
                    "expected_duration_min": 35,
                    "congestion_level": 3,
                    "congestion_description": "보통",
                    "time_saved_min": 15,
                    "reward_amount": 80
                }
            ]
        }
