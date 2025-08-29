import math
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer

# 기존 데이터 로더/클리너 재사용
from .views import load_merchants_data, clean_merchant_data


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    두 좌표 간 거리를 Haversine 공식으로 계산하여 미터 단위로 반환.
    """
    R = 6371000  # meters
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@extend_schema(
    tags=["Merchants"],
    summary="현재 위치 기반 근접 매장 검색 (피그마 카드용)",
    parameters=[
        OpenApiParameter('lat', float, description='현재 위도 (필수)'),
        OpenApiParameter('lng', float, description='현재 경도 (필수)'),
        OpenApiParameter('radius', float, description='검색 반경 미터 (기본 5000, 최대 20000)'),
        OpenApiParameter('limit', int, description='최대 결과 개수 (기본 10, 최대 10)'),
        OpenApiParameter('category', str, description='카테고리 필터 (선택)'),
        OpenApiParameter('q', str, description='상호 검색어 (선택)'),
    ],
    responses={
        200: inline_serializer(
            name='NearbyMerchantsResponseV1',
            fields={
                'merchants': serializers.ListField(
                    child=inline_serializer(
                        name='NearbyMerchantCardItem',
                        fields={
                            'id': serializers.CharField(),
                            'name': serializers.CharField(),
                            'category': serializers.CharField(),
                            'address': serializers.CharField(),
                            'lat': serializers.FloatField(),
                            'lng': serializers.FloatField(),
                            'distance_m': serializers.IntegerField(),
                        }
                    )
                ),
                'search_info': inline_serializer(
                    name='NearbySearchInfoV1',
                    fields={
                        'center': inline_serializer(
                            name='NearbySearchCenter',
                            fields={
                                'lat': serializers.FloatField(),
                                'lng': serializers.FloatField(),
                            }
                        ),
                        'radius_m': serializers.IntegerField(),
                        'total_found': serializers.IntegerField(),
                        'limit_applied': serializers.BooleanField(),
                    }
                )
            }
        ),
        400: inline_serializer(
            name='NearbyBadRequest',
            fields={'error': serializers.CharField()},
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_merchants(request):
    """
    현재 위치 기준 반경 내 가까운 매장을 거리순으로 반환.

    - 응답은 피그마 카드에 맞는 축약 필드 형태(id, name, category, address, distance_m, lat, lng)
    - 기본 반경 5km, 최대 20km
    - 기본 최대 10개, 최대 10개
    """
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return Response({'error': 'lat,lng 파라미터가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return Response({'error': '위도/경도 범위를 확인하세요.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        radius = float(request.GET.get('radius', 5000))
        radius = max(100, min(radius, 20000))  # 100m~20km
    except (TypeError, ValueError):
        radius = 5000

    try:
        limit = int(request.GET.get('limit', 10))
        limit = max(1, min(limit, 10))
    except (TypeError, ValueError):
        limit = 10

    category_filter = (request.GET.get('category') or '').strip()
    q = (request.GET.get('q') or '').strip()

    raw = load_merchants_data()
    items = []

    for m in raw:
        data = clean_merchant_data(m)
        if not data:
            continue

        if category_filter and category_filter not in data['category']:
            continue
        if q and q not in data['name']:
            continue

        d = haversine_distance(lat, lng, data['lat'], data['lng'])
        if d <= radius:
            items.append({
                'id': data['id'],
                'name': data['name'],
                'category': data['category'],
                'address': data['address'],
                'lat': data['lat'],
                'lng': data['lng'],
                'distance_m': int(round(d)),
            })

    # 거리순 정렬 후 제한
    items.sort(key=lambda x: x['distance_m'])
    limit_applied = len(items) > limit
    items = items[:limit]

    return Response({
        'merchants': items,
        'search_info': {
            'center': {'lat': lat, 'lng': lng},
            'radius_m': int(radius),
            'total_found': len(items),
            'limit_applied': limit_applied,
        }
    })
