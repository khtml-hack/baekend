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
    get_time_bucket_info
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
    
    def test_get_time_bucket_info(self):
        """시간대 버킷 정보 테스트"""
        # 오후 시간대 테스트
        bucket_info = get_time_bucket_info(self.test_time)
        self.assertIn('code', bucket_info)
        self.assertIn('name', bucket_info)
        
        # 새벽 시간대 테스트
        dawn_time = datetime(2025, 8, 9, 3, 0)
        dawn_bucket = get_time_bucket_info(dawn_time)
        self.assertEqual(dawn_bucket['code'], 'T6')
    
    @patch('trips.services.congestion_service.get_optimized_congestion_data')
    def test_get_optimal_time_window(self, mock_get_data):
        """최적 시간 추천 테스트"""
        mock_get_data.return_value = self.mock_congestion_data
        
        result = get_optimal_time_window(
            current_time=self.test_time,
            window_hours=2,
            location="default"
        )
        
        # 응답 구조 검증
        self.assertIn('optimal_window', result)
        self.assertIn('alternatives', result)
        self.assertIn('recommendation_reason', result)
        self.assertIn('search_parameters', result)
        
        # 최적 시간대 정보 검증
        optimal = result['optimal_window']
        self.assertIn('slot_start', optimal)
        self.assertIn('congestion_score', optimal)
        self.assertIn('recommendation_level', optimal)


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
        self.assertIn('optimal_window', data)
        self.assertIn('alternatives', data)
        self.assertIn('recommendation_reason', data)
    
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
        search_params = data['search_parameters']
        self.assertEqual(search_params['location'], 'gangnam')
        self.assertGreater(search_params['total_slots_analyzed'], 0)
    
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
    
    def test_recommendation_create(self):
        """여행 추천 생성 테스트"""
        url = reverse('trips:recommend')
        data = {
            'origin_address': '서울시 강남구',
            'destination_address': '서울시 홍대',
            'region_code': 'seoul'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
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
