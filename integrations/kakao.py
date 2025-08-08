"""
Kakao API Integration Module
"""
import requests
from django.conf import settings


def address_search(query):
    """
    Kakao 주소 검색 API
    
    Args:
        query (str): 검색할 주소
        
    Returns:
        dict: API 응답 데이터
    """
    if not settings.KAKAO_API_KEY:
        raise ValueError("KAKAO_API_KEY가 설정되지 않았습니다.")
    
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {
        "Authorization": f"KakaoAK {settings.KAKAO_API_KEY}"
    }
    params = {
        "query": query
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kakao 주소 검색 API 호출 실패: {str(e)}")


def keyword_search(query, x=None, y=None, radius=20000):
    """
    Kakao 키워드 검색 API
    
    Args:
        query (str): 검색 키워드
        x (float): 경도 (선택사항)
        y (float): 위도 (선택사항)  
        radius (int): 검색 반경 (미터, 기본값: 20000)
        
    Returns:
        dict: API 응답 데이터
    """
    if not settings.KAKAO_API_KEY:
        raise ValueError("KAKAO_API_KEY가 설정되지 않았습니다.")
    
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {
        "Authorization": f"KakaoAK {settings.KAKAO_API_KEY}"
    }
    params = {
        "query": query
    }
    
    # 좌표가 제공된 경우 추가
    if x is not None and y is not None:
        params.update({
            "x": x,
            "y": y,
            "radius": radius
        })
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kakao 키워드 검색 API 호출 실패: {str(e)}")


def category_search(lat, lng, code="FD6", radius=2000):
    """
    Kakao 카테고리 검색 API
    
    Args:
        lat (float): 위도
        lng (float): 경도
        code (str): 카테고리 코드 (기본값: FD6 - 음식점)
        radius (int): 검색 반경 (미터, 기본값: 2000)
        
    Returns:
        dict: API 응답 데이터
    """
    if not settings.KAKAO_API_KEY:
        raise ValueError("KAKAO_API_KEY가 설정되지 않았습니다.")
    
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {
        "Authorization": f"KakaoAK {settings.KAKAO_API_KEY}"
    }
    params = {
        "category_group_code": code,
        "x": lng,  # 경도
        "y": lat,  # 위도
        "radius": radius
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Kakao 카테고리 검색 API 호출 실패: {str(e)}")


# 기존 함수 유지 (하위 호환성)
def search_address(address):
    """
    Kakao 주소 검색 API를 사용하여 주소를 정규화/확인
    (기존 함수 - 하위 호환성 유지)
    """
    if not settings.KAKAO_API_KEY:
        raise ValueError("Kakao API Key가 설정되지 않았습니다.")
    
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {
        "Authorization": f"KakaoAK {settings.KAKAO_API_KEY}"
    }
    params = {
        "query": address
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get('documents'):
            doc = data['documents'][0]
            return {
                'normalized_address': doc.get('address_name', address),
                'x': doc.get('x'),  # 경도
                'y': doc.get('y'),  # 위도
                'region_1depth_name': doc.get('address', {}).get('region_1depth_name'),
                'region_2depth_name': doc.get('address', {}).get('region_2depth_name'),
                'region_3depth_name': doc.get('address', {}).get('region_3depth_name'),
            }
        else:
            return {'normalized_address': address}
            
    except requests.exceptions.RequestException as e:
        print(f"Kakao API 호출 실패: {e}")
        return {'normalized_address': address}
