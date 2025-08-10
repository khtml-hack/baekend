from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open
import json

from .models import Recommendation, Trip
from .services.congestion_service import (
    get_optimal_time_window, 
    calculate_congestion_score,
    get_precise_departure_time
)

User = get_user_model()


class CongestionServiceTestCase(TestCase):
    """혼잡도 서비스 테스트"""
    
    def setUp(self):
        self.test_time = datetime(2025, 8, 9, 14, 30)  # 금요일 오후 2:30
        self.mock_congestion_data = {
            "monthly_congestion": {
                "T0": 2.1, "T1": 1.8, "T2": 3.2, "T3": 2.7
            },
            "hourly_patterns": {
                "friday": {
                    "14": 3.3, "15": 3.0, "16": 3.5, "17": 4.5
                }
            },
            "special_events": {
                "rush_hour_multiplier": 1.3,
                "weekend_multiplier": 0.8
            },
            "location_factors": {
                "gangnam": 1.2,
                "default": 1.0
            }
        }
    
    @patch('trips.services.congestion_service.get_optimized_congestion_data')
    def test_calculate_congestion_score(self, mock_get_data):
        """혼잡도 점수 계산 테스트"""
        mock_get_data.return_value = self.mock_congestion_data
        
        # 기본 위치 테스트
        score = calculate_congestion_score(self.test_time, "default")
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 5.0)
        
        # 강남 위치 테스트 (1.2배 보정)
        gangnam_score = calculate_congestion_score(self.test_time, "gangnam")
        default_score = calculate_congestion_score(self.test_time, "default")
        self.assertGreater(gangnam_score, default_score)
    
    @patch('trips.services.congestion_service.get_optimized_congestion_data')
    def test_get_precise_departure_time(self, mock_get_data):
        """버킷 내 정확한 한 시각 추천 테스트"""
        mock_get_data.return_value = self.mock_congestion_data
        result = get_precise_departure_time('T1', date_ref=self.test_time, location='default')
        self.assertIsNotNone(result)
        self.assertIn('optimal_departure', result)
        self.assertIn('congestion_score', result)
    
    @patch('trips.services.congestion_service.get_optimized_congestion_data')
    def test_get_optimal_time_window(self, mock_get_data):
        """최적 시간 추천 테스트"""
        mock_get_data.return_value = self.mock_congestion_data
        
        result = get_optimal_time_window(
            current_time=self.test_time,
            window_hours=2,
            location="default"
        )
        
        # 응답 구조 검증 (신규 스키마)
        self.assertIn('optimal_time', result)
        self.assertIn('alternative_times', result)
        self.assertIn('search_window', result)
        self.assertIn('all_minutes_analyzed', result)
        
        # 최적 시간 정보 검증
        optimal = result['optimal_time']
        self.assertIn('time', optimal)
        self.assertIn('congestion_score', optimal)


class TripAPITestCase(APITestCase):
    """여행 API 테스트"""
    
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
    
    def test_optimal_travel_time_api(self):
        """최적 여행 시간 API 테스트"""
        url = reverse('trips:optimal-time')
        
        # 기본 요청 테스트
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('optimal_time', data)
        self.assertIn('alternative_times', data)
        self.assertIn('search_window', data)
    
    def test_optimal_travel_time_with_parameters(self):
        """파라미터를 포함한 최적 시간 API 테스트"""
        url = reverse('trips:optimal-time')
        params = {
            'window_hours': 3,
            'current_time': '2025-08-09 15:00',
            'location': 'gangnam'
        }
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data.get('location'), 'gangnam')
        self.assertGreater(data.get('analyzed_minutes', 0), 0)
    
    def test_optimal_travel_time_invalid_time_format(self):
        """잘못된 시간 형식 테스트"""
        url = reverse('trips:optimal-time')
        params = {'current_time': 'invalid-time-format'}
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        self.assertIn('error', data)
    
    def test_optimal_travel_time_unauthorized(self):
        """인증되지 않은 사용자 테스트"""
        self.client.credentials()  # 인증 정보 제거
        url = reverse('trips:optimal-time')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RecommendationTestCase(APITestCase):
    """여행 추천 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    @patch('integrations.kakao.search_address')
    @patch('trips.services.recommend_service.get_travel_recommendation')
    def test_recommendation_create(self, mock_get_travel_recommendation, mock_search_address):
        """여행 추천 생성 테스트"""
        # Kakao API 호출 모킹
        mock_search_address.return_value = {
            'normalized_address': '서울시 강남구 역삼동',
            'lat': 37.501234,
            'lng': 127.039876
        }
        
        # AI 추천 서비스 모킹 (신규 응답 스키마)
        mock_get_travel_recommendation.return_value = {
            'recommended_bucket': 'T3',
            'recommended_window': { 'start': '19:00', 'end': '21:00' },
            'optimal_departure_time': '19:12',
            'expected_duration_min': 34,
            'expected_congestion_level': 2,
            'rationale': '테스트 근거'
        }
        
        url = reverse('trips:recommend')
        data = {
            'origin_address': '서울시 강남구',
            'destination_address': '서울시 홍대',
            'region_code': 'seoul'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertIn('optimal_departure_time', body)
        
        # 데이터베이스에 추천이 생성되었는지 확인
        self.assertTrue(
            Recommendation.objects.filter(user=self.user).exists()
        )
    
    def test_trip_history(self):
        """여행 이력 조회 테스트"""
        # 테스트 데이터 생성
        recommendation = Recommendation.objects.create(
            user=self.user,
            origin_address='서울시 강남구',
            destination_address='서울시 홍대',
            recommended_bucket='T1',
            window_start='09:00:00',
            window_end='11:00:00',
            expected_duration_min=30,
            rationale='테스트 추천'
        )
        
        Trip.objects.create(
            user=self.user,
            recommendation=recommendation,
            status='ongoing'
        )
        
        url = reverse('trips:trip-history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertGreater(len(data), 0)


class TripModelTestCase(TestCase):
    """여행 모델 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
    
    def test_recommendation_creation(self):
        """추천 생성 테스트"""
        recommendation = Recommendation.objects.create(
            user=self.user,
            origin_address='서울시 강남구',
            destination_address='서울시 홍대',
            recommended_bucket='T1',
            window_start='09:00:00',
            window_end='11:00:00',
            expected_duration_min=30,
            rationale='테스트 추천'
        )
        
        self.assertEqual(recommendation.user, self.user)
        self.assertEqual(recommendation.origin_address, '서울시 강남구')
        self.assertIsNotNone(recommendation.created_at)
    
    def test_trip_creation(self):
        """여행 생성 테스트"""
        recommendation = Recommendation.objects.create(
            user=self.user,
            origin_address='서울시 강남구',
            destination_address='서울시 홍대',
            recommended_bucket='T1',
            window_start='09:00:00',
            window_end='11:00:00',
            expected_duration_min=30,
            rationale='테스트 추천'
        )
        
        trip = Trip.objects.create(
            user=self.user,
            recommendation=recommendation,
            status='planned'
        )
        
        self.assertEqual(trip.status, 'planned')
        self.assertEqual(trip.recommendation, recommendation)
        self.assertIsNotNone(trip.created_at)
