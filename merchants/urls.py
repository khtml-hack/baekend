from django.urls import path
from . import views
from . import views_new

app_name = 'merchants'

urlpatterns = [
    # 제휴 상점 목록 (페이지네이션, 필터링, 검색)
    path('list/', views.merchants_list, name='list'),
    
    # 지도용 마커 데이터 (간소화된 좌표 정보)
    path('map/', views.merchants_map, name='map'),

    # 현재 위치 기반 근접 매장 검색
    path('nearby/', views_new.nearby_merchants, name='nearby'),
    
    # 필터링 옵션 (지역, 카테고리 목록) - 반드시 detail보다 먼저!
    path('filters/', views.merchant_filters, name='filters'),
    
    # 상점 상세 정보
    path('<str:merchant_id>/', views.merchant_detail, name='detail'),
]
