import json
import os
import math
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings


def calculate_distance(lat1, lng1, lat2, lng2):
    """
    두 좌표 간의 거리 계산 (킬로미터)
    """
    if not all([lat1, lng1, lat2, lng2]):
        return float('inf')
    
    # 하버사인 공식
    R = 6371  # 지구 반지름 (킬로미터)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def load_merchants_data():
    """
    제휴 상점 JSON 데이터 로드
    """
    json_file_path = os.path.join(settings.BASE_DIR, 'merchants', 'fixtures', 'merchants_data.json')
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # JSON이 배열 형태로 되어있음
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def format_merchant_data(merchant):
    """
    원본 데이터를 API 응답용으로 변환
    """
    return {
        'id': f"merchant_{hash(merchant.get('시설명', ''))}",
        'name': merchant.get('시설명', ''),
        'category': merchant.get('카테고리2', ''),
        'subcategory': merchant.get('카테고리3', ''),
        'phone': merchant.get('전화번호', '정보없음'),
        'address': merchant.get('지번주소', ''),
        'road_address': merchant.get('도로명주소', ''),
        'x': str(merchant.get('경도', '')),  # 경도
        'y': str(merchant.get('위도', '')),  # 위도
        'postal_code': merchant.get('우편번호', ''),
        'weekday_hours': merchant.get('평일 운영시간', '정보없음'),
        'weekend_hours': merchant.get('주말 운영시간', '정보없음'),
        'free_parking': merchant.get('무료주차 가능여부', '정보없음'),
        'valet_parking': merchant.get('발렛주차 가능여부', '정보없음'),
        'pet_friendly': merchant.get('애완동물 동반입장 가능여부', '정보없음'),
        'vegetarian_menu': merchant.get('채식메뉴 보유여부', '정보없음'),
        'halal_menu': merchant.get('할랄음식 여부', '정보없음'),
        'wheelchair_accessible': merchant.get('휠체어 보유여부', '정보없음'),
        'region': f"{merchant.get('시도 명칭', '')} {merchant.get('시군구 명칭', '')}".strip()
    }


@api_view(['GET'])
def search_merchants(request):
    """
    제휴 상점 검색 API
    
    Query Parameters:
    - query: 검색 키워드 (상점명, 카테고리로 필터링)
    - lat: 위도 (거리 기반 정렬용)
    - lng: 경도 (거리 기반 정렬용)
    - radius: 검색 반경 (킬로미터, 기본값: 10)
    - region: 지역 필터 (예: 서울특별시, 경기도)
    - category: 카테고리 필터 (예: 한식, 중식, 일식)
    - page: 페이지 번호 (기본값: 1)
    - page_size: 페이지 크기 (기본값: 20)
    """
    query = request.GET.get('query', '').strip().lower()
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius = float(request.GET.get('radius', 10))  # 기본 10km
    region_filter = request.GET.get('region', '').strip()
    category_filter = request.GET.get('category', '').strip().lower()
    
    # 페이지네이션 파라미터
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
    except (ValueError, TypeError):
        page = 1
        page_size = 20
    
    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
    except (ValueError, TypeError):
        lat = lng = None
    
    # 제휴 상점 데이터 로드
    merchants = load_merchants_data()
    
    # 기본 필터링 (전화번호가 있는 곳만)
    filtered_merchants = []
    for merchant in merchants:
        # 기본 정보가 있는지 체크
        if not merchant.get('시설명') or not merchant.get('위도') or not merchant.get('경도'):
            continue
            
        # 지역 필터
        if region_filter:
            region = f"{merchant.get('시도 명칭', '')} {merchant.get('시군구 명칭', '')}".strip()
            if region_filter not in region:
                continue
        
        # 카테고리 필터
        if category_filter:
            category2 = merchant.get('카테고리2', '').lower()
            category3 = merchant.get('카테고리3', '').lower()
            if category_filter not in category2 and category_filter not in category3:
                continue
        
        # 키워드 필터링
        if query:
            name = merchant.get('시설명', '').lower()
            category2 = merchant.get('카테고리2', '').lower()
            category3 = merchant.get('카테고리3', '').lower()
            address = merchant.get('도로명주소', '').lower()
            
            if not any(query in field for field in [name, category2, category3, address]):
                continue
        
        filtered_merchants.append(merchant)
    
    # 거리 기반 필터링 및 정렬
    result_merchants = []
    if lat and lng:
        for merchant in filtered_merchants:
            try:
                m_lat = float(merchant.get('위도', 0))
                m_lng = float(merchant.get('경도', 0))
                distance = calculate_distance(lat, lng, m_lat, m_lng)
                
                if distance <= radius:
                    formatted_merchant = format_merchant_data(merchant)
                    formatted_merchant['distance'] = round(distance, 2)
                    result_merchants.append(formatted_merchant)
            except (ValueError, TypeError):
                continue
        
        # 거리순 정렬
        result_merchants = sorted(result_merchants, key=lambda x: x.get('distance', float('inf')))
    else:
        # 거리 정보 없이 모든 결과 반환
        for merchant in filtered_merchants:
            result_merchants.append(format_merchant_data(merchant))
    
    # 페이지네이션 적용
    total_count = len(result_merchants)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_merchants = result_merchants[start_idx:end_idx]
    
    return Response({
        'merchants': paginated_merchants,
        'meta': {
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'query': query,
            'region': region_filter,
            'category': category_filter,
            'location': {'lat': lat, 'lng': lng} if lat and lng else None,
            'radius_km': radius if lat and lng else None
        }
    })
