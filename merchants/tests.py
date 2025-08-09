from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import json
from unittest.mock import patch


class MerchantsAPITestCase(APITestCase):
    """제휴 상점 API 테스트"""
    
    def setUp(self):
        # 테스트용 상점 데이터
        self.mock_merchants_data = [
            {
                '번호': '1',
                '시설명': '테스트 카페',
                '카테고리2': '카페',
                '카테고리3': '커피전문점',
                '소재지 전체주소': '서울시 강남구 테스트로 123',
                '시도 명칭': '서울특별시',
                '시군구 명칭': '강남구',
                '위도': '37.5665',
                '경도': '126.9780',
                '전화번호': '02-1234-5678',
                '평일 운영시간': '09:00~22:00',
                '주말 운영시간': '10:00~23:00',
                '무료주차 가능여부': '가능',
                '발렛주차 가능여부': '불가능',
                '애완동물 동반입장 가능여부': '가능',
                '채식메뉴 보유여부': '보유',
                '휠체어 보유여부': '보유'
            },
            {
                '번호': '2',
                '시설명': '테스트 레스토랑',
                '카테고리2': '음식점',
                '카테고리3': '한식',
                '소재지 전체주소': '부산시 해운대구 테스트로 456',
                '시도 명칭': '부산광역시',
                '시군구 명칭': '해운대구',
                '위도': '35.1595',
                '경도': '129.1604',
                '전화번호': '051-9876-5432',
                '평일 운영시간': '11:00~21:00',
                '주말 운영시간': '11:00~22:00',
                '무료주차 가능여부': '가능',
                '발렛주차 가능여부': '가능',
                '애완동물 동반입장 가능여부': '불가능',
                '채식메뉴 보유여부': '미보유',
                '휠체어 보유여부': '보유'
            },
            {
                '번호': '3',
                '시설명': '무효한 데이터',
                '카테고리2': '기타',
                '위도': '',  # 잘못된 데이터
                '경도': 'invalid'  # 잘못된 데이터
            }
        ]

    @patch('merchants.views.load_merchants_data')
    def test_merchants_list_api(self, mock_load_data):
        """제휴 상점 목록 API 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        url = reverse('merchants:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # 응답 구조 확인
        self.assertIn('merchants', data)
        self.assertIn('pagination', data)
        
        # 유효한 데이터만 반환되는지 확인 (3개 중 2개만 유효)
        self.assertEqual(len(data['merchants']), 2)
        
        # 첫 번째 상점 데이터 확인
        first_merchant = data['merchants'][0]
        self.assertEqual(first_merchant['name'], '테스트 카페')
        self.assertEqual(first_merchant['category'], '카페')
        self.assertEqual(first_merchant['lat'], 37.5665)
        self.assertEqual(first_merchant['lng'], 126.9780)

    @patch('merchants.views.load_merchants_data')
    def test_merchants_list_with_pagination(self, mock_load_data):
        """페이지네이션 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        url = reverse('merchants:list')
        response = self.client.get(url, {'page': 1, 'page_size': 1})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # 페이지네이션 확인
        self.assertEqual(len(data['merchants']), 1)
        self.assertEqual(data['pagination']['current_page'], 1)
        self.assertEqual(data['pagination']['page_size'], 1)
        self.assertEqual(data['pagination']['total_count'], 2)
        self.assertTrue(data['pagination']['has_next'])
        self.assertFalse(data['pagination']['has_previous'])

    @patch('merchants.views.load_merchants_data')
    def test_merchants_list_with_filters(self, mock_load_data):
        """필터링 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        url = reverse('merchants:list')
        
        # 지역 필터 테스트
        response = self.client.get(url, {'region': '서울'})
        data = response.json()
        self.assertEqual(len(data['merchants']), 1)
        self.assertEqual(data['merchants'][0]['name'], '테스트 카페')
        
        # 카테고리 필터 테스트
        response = self.client.get(url, {'category': '음식점'})
        data = response.json()
        self.assertEqual(len(data['merchants']), 1)
        self.assertEqual(data['merchants'][0]['name'], '테스트 레스토랑')
        
        # 검색 테스트
        response = self.client.get(url, {'search': '카페'})
        data = response.json()
        self.assertEqual(len(data['merchants']), 1)
        self.assertEqual(data['merchants'][0]['name'], '테스트 카페')

    @patch('merchants.views.load_merchants_data')
    def test_merchants_map_api(self, mock_load_data):
        """지도용 마커 API 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        url = reverse('merchants:map')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # 응답 구조 확인
        self.assertIn('markers', data)
        self.assertIn('total_count', data)
        
        # 마커 데이터 확인 (간소화된 정보만)
        self.assertEqual(len(data['markers']), 2)
        
        first_marker = data['markers'][0]
        expected_fields = ['id', 'name', 'lat', 'lng', 'category', 'address']
        for field in expected_fields:
            self.assertIn(field, first_marker)

    @patch('merchants.views.load_merchants_data')
    def test_merchants_map_with_limit(self, mock_load_data):
        """지도 API 제한 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        url = reverse('merchants:map')
        response = self.client.get(url, {'limit': 1})
        
        data = response.json()
        self.assertEqual(len(data['markers']), 1)
        self.assertTrue(data['limit_applied'])

    @patch('merchants.views.load_merchants_data')
    def test_merchant_detail_api(self, mock_load_data):
        """상점 상세 정보 API 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        url = reverse('merchants:detail', kwargs={'merchant_id': '1'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # 상세 정보 확인
        self.assertIn('merchant', data)
        merchant = data['merchant']
        self.assertEqual(merchant['name'], '테스트 카페')
        self.assertEqual(merchant['id'], '1')
        
        # 상세 필드 확인
        self.assertIn('hours', merchant)
        self.assertIn('amenities', merchant)

    @patch('merchants.views.load_merchants_data')
    def test_merchant_detail_not_found(self, mock_load_data):
        """존재하지 않는 상점 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        url = reverse('merchants:detail', kwargs={'merchant_id': '999'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertIn('error', data)

    @patch('merchants.views.load_merchants_data')
    def test_merchant_filters_api(self, mock_load_data):
        """필터 옵션 API 테스트"""
        mock_load_data.return_value = self.mock_merchants_data
        
        # 직접 views 함수를 import해서 테스트
        from merchants.views import merchant_filters
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/api/merchants/filters/')
        
        # 직접 함수 호출
        response = merchant_filters(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # 필터 옵션 확인
        self.assertIn('regions', data)
        self.assertIn('categories', data)
        self.assertIn('total_merchants', data)
        
        # 지역 목록 확인
        self.assertIn('서울특별시 강남구', data['regions'])
        self.assertIn('부산광역시 해운대구', data['regions'])
        
        # 카테고리 목록 확인
        self.assertIn('카페', data['categories'])
        self.assertIn('음식점', data['categories'])
        
        # 총 상점 수 확인 (유효한 데이터만)
        self.assertEqual(data['total_merchants'], 2)

    def test_clean_merchant_data_function(self):
        """데이터 정리 함수 테스트"""
        from merchants.views import clean_merchant_data
        
        # 정상 데이터
        valid_merchant = self.mock_merchants_data[0]
        result = clean_merchant_data(valid_merchant)
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], '테스트 카페')
        
        # 잘못된 데이터
        invalid_merchant = self.mock_merchants_data[2]
        result = clean_merchant_data(invalid_merchant)
        self.assertIsNone(result)
        
        # 빈 이름
        empty_name_merchant = {'시설명': '', '위도': '37.5', '경도': '126.9'}
        result = clean_merchant_data(empty_name_merchant)
        self.assertIsNone(result)


class MerchantsIntegrationTestCase(APITestCase):
    """통합 테스트"""
    
    def test_api_endpoints_accessibility(self):
        """모든 API 엔드포인트 접근성 테스트 (실제 데이터 사용)"""
        urls = [
            '/api/merchants/list/',
            '/api/merchants/map/',
            '/api/merchants/filters/',
        ]
        
        for url in urls:
            response = self.client.get(url)
            # 404가 아닌 응답이면 OK (데이터가 없어도 200이나 다른 유효한 상태)
            self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
