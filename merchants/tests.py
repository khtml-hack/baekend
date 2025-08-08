from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, mock_open
import json
from merchants.services.merchant_service import search_merchants, calculate_distance

User = get_user_model()


class MerchantServiceTestCase(TestCase):
    """제휴 상점 서비스 테스트"""
    
    def setUp(self):
        # 테스트용 상점 데이터
        self.test_merchants = [
            {
                'name': '테스트 카페',
                'category': '카페',
                'latitude': 37.5665,
                'longitude': 126.9780,
                'address': '서울시 강남구',
                'phone': '02-1234-5678'
            },
            {
                'name': '테스트 레스토랑',
                'category': '한식',
                'latitude': 37.5670,
                'longitude': 126.9785,
                'address': '서울시 강남구',
                'phone': '02-1234-5679'
            }
        ]
    
    def test_calculate_distance(self):
        """거리 계산 테스트"""
        # 서울역과 강남역 사이의 거리 (약 8.1km)
        distance = calculate_distance(37.5547, 126.9707, 37.4979, 127.0276)
        self.assertGreater(distance, 7)
        self.assertLess(distance, 9)  # 8.1km이므로 9km 이하로 수정
    
    @patch('merchants.services.merchant_service.load_merchant_data')
    def test_search_merchants_by_keyword(self, mock_load_data):
        """키워드로 상점 검색 테스트"""
        mock_load_data.return_value = [
            {
                'name': '테스트 카페',
                'category': '카페',
                'description': '맛있는 커피',
                'latitude': 37.5665,
                'longitude': 126.9780
            }
        ]
        
        result = search_merchants(keyword='카페')
        self.assertEqual(len(result), 1)
        self.assertIn('카페', result[0]['name'])
    
    @patch('merchants.services.merchant_service.load_merchant_data')
    def test_search_merchants_by_category(self, mock_load_data):
        """카테고리로 상점 검색 테스트"""
        mock_load_data.return_value = [
            {
                'name': '테스트 카페',
                'category': '카페',
                'description': '맛있는 커피',
                'latitude': 37.5665,
                'longitude': 126.9780
            }
        ]
        
        result = search_merchants(category='카페')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['category'], '카페')
    
    @patch('merchants.services.merchant_service.load_merchant_data')
    def test_search_merchants_distance_filter(self, mock_load_data):
        """거리 필터링 테스트"""
        mock_load_data.return_value = [
            {
                'name': '가까운 카페',
                'category': '카페',
                'latitude': 37.5665,
                'longitude': 126.9780
            },
            {
                'name': '먼 카페',
                'category': '카페',
                'latitude': 37.6665,  # 약 11km 떨어진 곳
                'longitude': 126.9780
            }
        ]
        
        # 5km 반경 내 검색
        result = search_merchants(
            user_lat=37.5665,
            user_lng=126.9780,
            max_distance=5
        )
        
        # 가까운 카페만 결과에 포함되어야 함
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], '가까운 카페')
    
    @patch('merchants.services.merchant_service.load_merchant_data')
    def test_search_merchants_sorting(self, mock_load_data):
        """검색 결과 정렬 테스트"""
        mock_load_data.return_value = [
            {
                'name': '먼 카페',
                'category': '카페',
                'latitude': 37.5670,
                'longitude': 126.9785
            },
            {
                'name': '가까운 카페',
                'category': '카페',
                'latitude': 37.5665,
                'longitude': 126.9780
            }
        ]
        
        result = search_merchants(
            user_lat=37.5665,
            user_lng=126.9780,
            max_distance=10
        )
        
        # 거리순으로 정렬되어야 함
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], '가까운 카페')
        self.assertLess(result[0]['distance'], result[1]['distance'])


class MerchantAPITestCase(APITestCase):
    """제휴 상점 API 테스트"""
    
    def setUp(self):
        # 테스트 사용자 생성
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        # JWT 토큰 생성
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # API 클라이언트 인증 설정
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Mock 데이터 (실제 API 형식에 맞게)
        self.mock_merchant_data = [
            {
                "시설명": "API 테스트 카페",
                "카테고리2": "카페",
                "카테고리3": "커피전문점",
                "시도 명칭": "서울특별시",
                "시군구 명칭": "강남구",
                "도로명주소": "서울특별시 강남구 API테스트로 123",
                "위도": "37.5665",
                "경도": "126.9780",
                "전화번호": "02-1111-2222",
                "우편번호": "06298"
            }
        ]
    
    @patch('merchants.views.load_merchants_data')
    def test_merchant_search_api(self, mock_load_data):
        """상점 검색 API 테스트"""
        mock_load_data.return_value = self.mock_merchant_data
        
        url = reverse('merchants:search')
        params = {
            'query': '카페',
            'lat': 37.5665,
            'lng': 126.9780,
            'radius': 5
        }
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('merchants', data)
        self.assertIn('meta', data)
        self.assertIn('total_count', data['meta'])
        
        merchants = data['merchants']
        self.assertGreater(len(merchants), 0)
        self.assertEqual(merchants[0]['name'], 'API 테스트 카페')
    
    @patch('merchants.views.load_merchants_data')
    def test_merchant_search_api_with_category(self, mock_load_data):
        """카테고리 검색 API 테스트"""
        mock_load_data.return_value = self.mock_merchant_data
        
        url = reverse('merchants:search')
        params = {'category': '카페'}
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        meta = data['meta']
        self.assertEqual(meta['category'], '카페')
    
    def test_merchant_search_api_missing_coordinates(self):
        """좌표 누락 시 정상 검색 테스트"""
        url = reverse('merchants:search')
        params = {'query': '카페'}  # 좌표 누락이지만 정상 동작해야 함
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('merchants', data)
        self.assertIn('meta', data)
        # 좌표가 없으면 location 정보가 None이어야 함
        self.assertIsNone(data['meta']['location'])
    
    def test_merchant_search_api_invalid_coordinates(self):
        """잘못된 좌표 형식 테스트"""
        url = reverse('merchants:search')
        params = {
            'query': '카페',
            'lat': 'invalid',
            'lng': 'invalid'
        }
        
        response = self.client.get(url, params)
        # 잘못된 좌표는 무시되고 정상 검색이 되어야 함
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('merchants', data)
        # 잘못된 좌표는 None으로 처리되어야 함
        self.assertIsNone(data['meta']['location'])
    
    def test_merchant_search_api_unauthorized(self):
        """인증되지 않은 사용자 테스트"""
        self.client.credentials()  # 인증 정보 제거
        
        url = reverse('merchants:search')
        params = {
            'query': '카페',
            'lat': 37.5665,
            'lng': 126.9780
        }
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('merchants.views.load_merchants_data')
    def test_merchant_search_api_pagination(self, mock_load_data):
        """페이지네이션 테스트"""
        # 여러 개의 상점 데이터 생성 (실제 API 형식에 맞게)
        multiple_merchants = []
        for i in range(25):
            merchant = {
                "시설명": f"페이지네이션 테스트 상점 {i}",
                "카테고리2": "카페",
                "카테고리3": "커피전문점",
                "시도 명칭": "서울특별시",
                "시군구 명칭": "강남구",
                "도로명주소": f"서울특별시 강남구 테스트로 {i}",
                "위도": str(37.5665 + (i * 0.0001)),
                "경도": str(126.9780 + (i * 0.0001)),
                "전화번호": f"02-{i:04d}-{i:04d}",
                "우편번호": "06298"
            }
            multiple_merchants.append(merchant)
        
        mock_load_data.return_value = multiple_merchants
        
        url = reverse('merchants:search')
        params = {
            'query': '페이지네이션',
            'lat': 37.5665,
            'lng': 126.9780,
            'page': 1,
            'page_size': 10
        }
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(len(data['merchants']), 10)  # 페이지 크기만큼
        self.assertEqual(data['meta']['total_count'], 25)  # 전체 개수