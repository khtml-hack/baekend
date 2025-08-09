"""
Common utility functions
"""
import re
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError


def validate_korean_phone_number(phone_number: str) -> bool:
    """
    한국 전화번호 유효성 검증
    
    Args:
        phone_number (str): 검증할 전화번호
        
    Returns:
        bool: 유효하면 True, 아니면 False
    """
    if not phone_number:
        return False
    
    # 하이픈, 공백, 괄호 제거
    cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)
    
    # 한국 전화번호 패턴
    patterns = [
        r'^010\d{8}$',  # 휴대폰: 010-XXXX-XXXX
        r'^02\d{7,8}$',  # 서울: 02-XXX-XXXX, 02-XXXX-XXXX
        r'^0[3-6]\d{1}\d{7,8}$',  # 지역번호: 031-XXX-XXXX
        r'^070\d{8}$',  # 인터넷 전화: 070-XXXX-XXXX
        r'^080\d{7}$',   # 무료 전화: 080-XXX-XXXX
    ]
    
    return any(re.match(pattern, cleaned) for pattern in patterns)


def format_phone_number(phone_number: str) -> str:
    """
    전화번호를 표준 형식으로 포맷팅
    
    Args:
        phone_number (str): 포맷팅할 전화번호
        
    Returns:
        str: 포맷팅된 전화번호 (예: 010-1234-5678)
    """
    if not validate_korean_phone_number(phone_number):
        raise ValidationError("유효하지 않은 전화번호입니다.")
    
    cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)
    
    if cleaned.startswith('010'):
        return f"{cleaned[:3]}-{cleaned[3:7]}-{cleaned[7:]}"
    elif cleaned.startswith('02'):
        if len(cleaned) == 9:  # 02-XXX-XXXX
            return f"{cleaned[:2]}-{cleaned[2:5]}-{cleaned[5:]}"
        else:  # 02-XXXX-XXXX
            return f"{cleaned[:2]}-{cleaned[2:6]}-{cleaned[6:]}"
    elif cleaned.startswith('070'):
        return f"{cleaned[:3]}-{cleaned[3:7]}-{cleaned[7:]}"
    else:
        # 기타 지역번호 (3자리-3/4자리-4자리)
        return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"


def calculate_age_from_korean_id(resident_id: str) -> Optional[int]:
    """
    주민등록번호에서 나이 계산
    
    Args:
        resident_id (str): 주민등록번호 (6자리 또는 13자리)
        
    Returns:
        Optional[int]: 계산된 나이, 유효하지 않으면 None
    """
    if not resident_id:
        return None
    
    # 하이픈 제거
    cleaned = resident_id.replace('-', '')
    
    if len(cleaned) < 7:
        return None
    
    try:
        birth_year = int(cleaned[:2])
        birth_month = int(cleaned[2:4])
        birth_day = int(cleaned[4:6])
        
        if len(cleaned) >= 7:
            gender_code = int(cleaned[6])
        else:
            return None
        
        # 세기 판별
        if gender_code in [1, 2]:
            birth_year += 1900
        elif gender_code in [3, 4]:
            birth_year += 2000
        else:
            return None
        
        # 나이 계산
        today = datetime.now()
        age = today.year - birth_year
        
        # 생일이 지나지 않았으면 1 빼기
        if today.month < birth_month or (today.month == birth_month and today.day < birth_day):
            age -= 1
            
        return age
        
    except (ValueError, IndexError):
        return None


def mask_personal_info(text: str, info_type: str = 'phone') -> str:
    """
    개인정보 마스킹 처리
    
    Args:
        text (str): 마스킹할 텍스트
        info_type (str): 정보 타입 ('phone', 'email', 'name')
        
    Returns:
        str: 마스킹된 텍스트
    """
    if not text:
        return text
    
    if info_type == 'phone':
        # 전화번호 마스킹: 010-****-5678, 01012345678 -> 010****5678, 02-123-4567 -> 02-****-4567
        # 하이픈이 있는 경우
        if '-' in text:
            # 010-1234-5678 패턴
            pattern1 = r'(\d{3})-(\d{4})-(\d{4})'
            match1 = re.match(pattern1, text)
            if match1:
                return f"{match1.group(1)}-****-{match1.group(3)}"
            
            # 02-123-4567 또는 02-1234-5678 패턴
            pattern2 = r'(\d{2,3})-(\d{3,4})-(\d{4})'
            match2 = re.match(pattern2, text)
            if match2:
                return f"{match2.group(1)}-****-{match2.group(3)}"
        else:
            # 하이픈이 없는 경우: 01012345678 -> 010****5678
            if len(text) == 11 and text.startswith('010'):
                return f"{text[:3]}****{text[7:]}"
            elif len(text) == 10 and text.startswith('02'):
                return f"{text[:2]}****{text[6:]}"
            elif len(text) == 11 and text.startswith(('031', '032', '033', '041', '042', '043', '051', '052', '053', '054', '055', '061', '062', '063', '064', '070')):
                return f"{text[:3]}****{text[7:]}"
        
        # 기본 패턴으로 처리
        pattern = r'(\d{3})(\d{4})(\d{4})'
        return re.sub(pattern, r'\1****\3', text)
    
    elif info_type == 'email':
        # 이메일 마스킹: abc****@example.com
        if '@' in text:
            local, domain = text.split('@', 1)
            if len(local) > 3:
                masked_local = local[:3] + '*' * (len(local) - 3)
            else:
                masked_local = local[0] + '*' * (len(local) - 1)
            return f"{masked_local}@{domain}"
    
    elif info_type == 'name':
        # 이름 마스킹: 김*호, 김**
        if len(text) == 2:
            return text[0] + '*'
        elif len(text) >= 3:
            return text[0] + '*' * (len(text) - 2) + text[-1]
    
    return text


def get_time_greeting() -> str:
    """
    현재 시간에 따른 인사말 반환
    
    Returns:
        str: 시간대별 인사말
    """
    current_hour = datetime.now().hour
    
    if 5 <= current_hour < 12:
        return "좋은 아침입니다"
    elif 12 <= current_hour < 18:
        return "좋은 오후입니다"
    elif 18 <= current_hour < 22:
        return "좋은 저녁입니다"
    else:
        return "안녕하세요"


def safe_divide(numerator: Union[int, float], denominator: Union[int, float], default: float = 0.0) -> float:
    """
    안전한 나눗셈 (0으로 나누기 방지)
    
    Args:
        numerator: 분자
        denominator: 분모
        default: 0으로 나눌 때 반환할 기본값
        
    Returns:
        float: 나눗셈 결과 또는 기본값
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    텍스트 자르기 (말줄임표 추가)
    
    Args:
        text (str): 자를 텍스트
        max_length (int): 최대 길이
        suffix (str): 말줄임표
        
    Returns:
        str: 잘린 텍스트
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_boolean(value: Union[str, bool, int, None]) -> bool:
    """
    다양한 타입의 값을 boolean으로 변환
    
    Args:
        value: 변환할 값
        
    Returns:
        bool: 변환된 boolean 값
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'on', 'y']
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    return False
