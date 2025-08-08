import json
import os
import math
from django.conf import settings


def load_merchant_data():
    """제휴 상점 데이터를 JSON 파일에서 로드"""
    json_path = os.path.join(settings.BASE_DIR, 'merchants', 'fixtures', 'merchants_data.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get('merchants', [])
    except FileNotFoundError:
        return []


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    두 좌표 간의 거리를 계산 (하버사인 공식 사용)
    결과는 킬로미터 단위로 반환
    """
    # 위도와 경도를 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 차이 계산
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # 하버사인 공식
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # 지구의 반지름 (킬로미터)
    earth_radius = 6371
    
    distance = earth_radius * c
    return distance


def search_merchants(keyword=None, category=None, user_lat=None, user_lng=None, 
                    max_distance=10, page=1, page_size=20):
    """
    제휴 상점 검색
    
    Args:
        keyword: 검색 키워드
        category: 카테고리 필터
        user_lat: 사용자 위도
        user_lng: 사용자 경도
        max_distance: 최대 거리 (km)
        page: 페이지 번호
        page_size: 페이지 크기
    
    Returns:
        list: 검색된 상점 목록
    """
    merchants = load_merchant_data()
    
    if not merchants:
        return []
    
    # 키워드 필터링
    if keyword:
        keyword_lower = keyword.lower()
        merchants = [
            merchant for merchant in merchants
            if (keyword_lower in merchant.get('name', '').lower() or
                keyword_lower in merchant.get('description', '').lower())
        ]
    
    # 카테고리 필터링
    if category:
        merchants = [
            merchant for merchant in merchants
            if merchant.get('category', '').lower() == category.lower()
        ]
    
    # 거리 계산 및 필터링
    if user_lat is not None and user_lng is not None:
        merchants_with_distance = []
        
        for merchant in merchants:
            merchant_lat = merchant.get('latitude')
            merchant_lng = merchant.get('longitude')
            
            if merchant_lat is not None and merchant_lng is not None:
                distance = calculate_distance(user_lat, user_lng, merchant_lat, merchant_lng)
                
                if distance <= max_distance:
                    merchant_copy = merchant.copy()
                    merchant_copy['distance'] = round(distance, 2)
                    merchants_with_distance.append(merchant_copy)
        
        # 거리순 정렬
        merchants = sorted(merchants_with_distance, key=lambda x: x['distance'])
    
    # 페이지네이션
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    return merchants[start_idx:end_idx]


def get_merchant_by_id(merchant_id):
    """ID로 특정 상점 조회"""
    merchants = load_merchant_data()
    
    for merchant in merchants:
        if merchant.get('id') == merchant_id:
            return merchant
    
    return None


def get_merchants_by_category(category, limit=10):
    """카테고리별 상점 목록 조회"""
    merchants = load_merchant_data()
    
    category_merchants = [
        merchant for merchant in merchants
        if merchant.get('category', '').lower() == category.lower()
    ]
    
    return category_merchants[:limit]


def get_nearby_merchants(user_lat, user_lng, radius=5, limit=20):
    """주변 상점 조회"""
    merchants = load_merchant_data()
    nearby_merchants = []
    
    for merchant in merchants:
        merchant_lat = merchant.get('latitude')
        merchant_lng = merchant.get('longitude')
        
        if merchant_lat is not None and merchant_lng is not None:
            distance = calculate_distance(user_lat, user_lng, merchant_lat, merchant_lng)
            
            if distance <= radius:
                merchant_copy = merchant.copy()
                merchant_copy['distance'] = round(distance, 2)
                nearby_merchants.append(merchant_copy)
    
    # 거리순 정렬 후 제한
    nearby_merchants.sort(key=lambda x: x['distance'])
    return nearby_merchants[:limit]
