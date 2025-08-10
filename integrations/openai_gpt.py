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
당신은 교통 혼잡도 전문가입니다. 주어진 데이터를 바탕으로 **2개의 최적 여행 시간 옵션**을 **분 단위까지 정확하게** 추천해주세요.

출발지: {origin_address}
목적지: {destination_address}
현재 월 혼잡도: {current_congestion_str}{pattern_info}

시간대 설명:
- T0 (06:00-08:00): 이른 아침 시간대
- T1 (08:00-10:00): 출근 시간대
- T2 (17:00-19:00): 퇴근 시간대  
- T3 (19:00-21:00): 저녁 시간대

**중요**: 2시간 이내에서 **2개의 다른 시간 옵션**을 추천해주세요.
1. **최적 시간**: 가장 혼잡도가 낮고 여행에 적합한 시간
2. **대안 시간**: 적당히 좋은 시간 (약간의 절약 효과)

다음 JSON 형식으로 응답해주세요:

{{
    "recommendations": [
        {{
            "option_type": "최적 시간",
            "recommended_bucket": "T0/T1/T2/T3 중 하나",
            "recommended_window": {{
                "start": "HH:MM (정확한 분 단위)",
                "end": "HH:MM (정확한 분 단위)"
            }},
            "optimal_departure_time": "HH:MM (가장 좋은 출발 시간)",
            "rationale": "추천 이유 설명 (구체적인 시간과 혼잡도 수치 포함)",
            "expected_duration_min": 예상 소요시간(분),
            "expected_congestion_level": 1-5 사이의 혼잡도 레벨,
            "congestion_description": "매우 혼잡/혼잡/보통/원활/매우 원활",
            "time_sensitivity": "시간 민감도 (높음/보통/낮음)",
            "time_saved_min": 예상 절약 시간(분),
            "reward_amount": 예상 보상 금액(원)
        }},
        {{
            "option_type": "대안 시간",
            "recommended_bucket": "T0/T1/T2/T3 중 하나",
            "recommended_window": {{
                "start": "HH:MM (정확한 분 단위)",
                "end": "HH:MM (정확한 분 단위)"
            }},
            "optimal_departure_time": "HH:MM (대안 출발 시간)",
            "rationale": "추천 이유 설명 (구체적인 시간과 혼잡도 수치 포함)",
            "expected_duration_min": 예상 소요시간(분),
            "expected_congestion_level": 1-5 사이의 혼잡도 레벨,
            "congestion_description": "매우 혼잡/혼잡/보통/원활/매우 원활",
            "time_sensitivity": "시간 민감도 (높음/보통/낮음)",
            "time_saved_min": 예상 절약 시간(분),
            "reward_amount": 예상 보상 금액(원)
        }}
    ],
    "current_time_analysis": {{
        "departure_time": "현재 출발 시 시간",
        "arrival_time": "현재 출발 시 도착 시간",
        "duration_min": "현재 출발 시 소요시간(분)",
        "congestion_level": "현재 출발 시 혼잡도 레벨",
        "congestion_description": "현재 출발 시 혼잡도 설명"
    }}
}}

**요구사항**:
1. 각 옵션의 recommended_window는 2시간 이내여야 함
2. 첫 번째 옵션은 가장 좋은 시간, 두 번째는 적당히 좋은 시간
3. 각 옵션별로 구체적인 혼잡도 수치와 시간을 포함
4. 현재 시간 출발 시와의 비교 정보 제공
5. 예상 절약 시간과 보상 금액 포함

JSON만 응답하고 다른 텍스트는 포함하지 마세요.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 교통 혼잡도 전문가입니다. 주어진 데이터를 바탕으로 2개의 최적 여행 시간 옵션을 분 단위까지 정확하게 추천해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.2
        )
        
        content = response.choices[0].message.content.strip()
        return json.loads(content)
        
    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}")
        # 기본값 반환
        return {
            "recommendations": [
                {
                    "option_type": "최적 시간",
                    "recommended_bucket": "T0",
                    "recommended_window": {"start": "06:00", "end": "08:00"},
                    "optimal_departure_time": "06:30",
                    "rationale": "혼잡도 데이터를 기반으로 한 기본 추천입니다. T0 시간대가 가장 혼잡도가 낮습니다.",
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
            ],
            "current_time_analysis": {
                "departure_time": "09:41",
                "arrival_time": "10:31",
                "duration_min": 50,
                "congestion_level": 5,
                "congestion_description": "매우 혼잡"
            }
        }
