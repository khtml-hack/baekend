import json
import os
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.conf import settings


def load_merchants_data():
    """제휴 상점 데이터를 JSON 파일에서 로드"""
    json_path = os.path.join(settings.BASE_DIR, 'merchants', 'fixtures', 'merchants_data.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def clean_merchant_data(merchant):
    """상점 데이터를 정리해서 반환"""
    try:
        lat = float(merchant.get('위도', 0))
        lng = float(merchant.get('경도', 0))
    except (ValueError, TypeError):
        return None
    
    name = merchant.get('시설명', '').strip()
    if not name or lat == 0 or lng == 0:
        return None
    
    return {
        'id': merchant.get('번호', ''),
        'name': name,
        'category': merchant.get('카테고리2', '기타'),
        'subcategory': merchant.get('카테고리3', ''),
        'address': merchant.get('소재지 전체주소', ''),
        'region': f"{merchant.get('시도 명칭', '')} {merchant.get('시군구 명칭', '')}".strip(),
        'lat': lat,
        'lng': lng,
        'phone': merchant.get('전화번호', ''),
        'hours': {
            'weekday': merchant.get('평일 운영시간', '정보없음'),
            'weekend': merchant.get('주말 운영시간', '정보없음')
        },
        'amenities': {
            'parking': merchant.get('무료주차 가능여부', '정보없음'),
            'valet': merchant.get('발렛주차 가능여부', '정보없음'), 
            'pet_friendly': merchant.get('애완동물 동반입장 가능여부', '정보없음'),
            'vegetarian': merchant.get('채식메뉴 보유여부', '정보없음'),
            'wheelchair': merchant.get('휠체어 보유여부', '정보없음')
        }
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def merchants_list(request):
    """
    제휴 상점 전체 목록 API
    
    Query Parameters:
    - page: 페이지 번호 (기본값: 1)
    - page_size: 페이지 크기 (기본값: 20, 최대: 100)
    - region: 지역 필터 (예: "서울", "부산")
    - category: 카테고리 필터 (예: "음식점", "카페")
    - search: 상점명 검색
    """
    # 파라미터 파싱
    try:
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)
    except (ValueError, TypeError):
        page = 1
        page_size = 20
    
    region_filter = request.GET.get('region', '').strip()
    category_filter = request.GET.get('category', '').strip()
    search_query = request.GET.get('search', '').strip()
    
    # 데이터 로드 및 정리
    raw_merchants = load_merchants_data()
    merchants = []
    
    for merchant in raw_merchants:
        clean_data = clean_merchant_data(merchant)
        if not clean_data:
            continue
            
        # 필터링
        if region_filter and region_filter not in clean_data['region']:
            continue
            
        if category_filter and category_filter not in clean_data['category']:
            continue
            
        if search_query and search_query not in clean_data['name']:
            continue
            
        merchants.append(clean_data)
    
    # 페이지네이션
    total_count = len(merchants)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_merchants = merchants[start_idx:end_idx]
    
    return Response({
        'merchants': paginated_merchants,
        'pagination': {
            'current_page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': (total_count + page_size - 1) // page_size,
            'has_next': end_idx < total_count,
            'has_previous': page > 1
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def merchants_map(request):
    """
    지도용 마커 데이터 API
    
    Query Parameters:
    - region: 지역 필터 (선택사항)
    - category: 카테고리 필터 (선택사항)
    - limit: 최대 개수 (기본값: 500, 최대: 2000)
    """
    region_filter = request.GET.get('region', '').strip()
    category_filter = request.GET.get('category', '').strip()
    limit = min(int(request.GET.get('limit', 500)), 2000)
    
    # 데이터 로드
    raw_merchants = load_merchants_data()
    markers = []
    
    for merchant in raw_merchants:
        clean_data = clean_merchant_data(merchant)
        if not clean_data:
            continue
            
        # 필터링
        if region_filter and region_filter not in clean_data['region']:
            continue
            
        if category_filter and category_filter not in clean_data['category']:
            continue
        
        # 지도용 간소화된 데이터
        markers.append({
            'id': clean_data['id'],
            'name': clean_data['name'],
            'lat': clean_data['lat'],
            'lng': clean_data['lng'],
            'category': clean_data['category'],
            'address': clean_data['address']
        })
        
        # 개수 제한
        if len(markers) >= limit:
            break
    
    return Response({
        'markers': markers,
        'total_count': len(markers),
        'limit_applied': len(markers) >= limit
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def merchant_detail(request, merchant_id):
    """
    개별 상점 상세 정보 API
    """
    raw_merchants = load_merchants_data()
    
    for merchant in raw_merchants:
        if str(merchant.get('번호', '')) == str(merchant_id):
            clean_data = clean_merchant_data(merchant)
            if clean_data:
                return Response({'merchant': clean_data})
    
    return Response({
        'error': '해당 상점을 찾을 수 없습니다.'
    }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def merchant_filters(request):
    """
    필터링 옵션 API (지역, 카테고리 목록)
    """
    raw_merchants = load_merchants_data()
    
    regions = set()
    categories = set()
    
    for merchant in raw_merchants:
        clean_data = clean_merchant_data(merchant)
        if not clean_data:
            continue
            
        if clean_data['region']:
            regions.add(clean_data['region'])
        if clean_data['category']:
            categories.add(clean_data['category'])
    
    return Response({
        'regions': sorted(list(regions)),
        'categories': sorted(list(categories)),
        'total_merchants': len([m for m in raw_merchants if clean_merchant_data(m)])
    })
