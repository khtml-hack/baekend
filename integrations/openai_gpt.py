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


def get_travel_recommendation(origin_address, destination_address, current_congestion, full_congestion_data=None):
    """
    OpenAI GPT를 사용하여 여행 추천 정보 생성
    current_congestion: 현재 월의 혼잡도 데이터
    full_congestion_data: 전체 월별 혼잡도 데이터 (패턴 분석용)
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
    
    prompt = f"""
다음 여행 계획에 대해 최적의 시간대를 추천해주세요:

출발지: {origin_address}
목적지: {destination_address}
현재 월 혼잡도: {current_congestion_str}{pattern_info}

시간대 설명:
- T0 (06:00-08:00): 이른 아침 시간대
- T1 (08:00-10:00): 출근 시간대
- T2 (17:00-19:00): 퇴근 시간대  
- T3 (19:00-21:00): 저녁 시간대

혼잡도가 가장 낮고 여행에 적합한 시간대를 선택하여 다음 JSON 형식으로 응답해주세요:

{{
    "recommended_bucket": "T0/T1/T2/T3 중 하나",
    "recommended_window": {{"start": "HH:MM", "end": "HH:MM"}},
    "rationale": "추천 이유 설명",
    "expected_duration_min": 예상 소요시간(분),
    "expected_congestion_level": 1-5 사이의 혼잡도 레벨
}}

JSON만 응답하고 다른 텍스트는 포함하지 마세요.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 교통 혼잡도 전문가입니다. 주어진 데이터를 바탕으로 최적의 여행 시간을 추천해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        return json.loads(content)
        
    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}")
        # 기본값 반환
        return {
            "recommended_bucket": "T0",
            "recommended_window": {"start": "06:00", "end": "08:00"},
            "rationale": "혼잡도 데이터를 기반으로 한 기본 추천입니다.",
            "expected_duration_min": 30,
            "expected_congestion_level": 3
        }
