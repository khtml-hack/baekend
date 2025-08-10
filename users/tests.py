from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import json

from .models import User
from .serializers import UserRegistrationSerializer, UserSerializer

User = get_user_model()


class UserModelTestCase(TestCase):
    """사용자 모델 테스트"""
    
    def test_create_user(self):
        """일반 사용자 생성 테스트"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('testpass123'))
    
    def test_create_superuser(self):
        """슈퍼유저 생성 테스트"""
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            username='admin'
        )
        
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
    
    def test_create_user_without_email(self):
        """이메일 없이 사용자 생성 시 에러 테스트"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                password='testpass123',
                username='testuser'
            )
    
    def test_user_string_representation(self):
        """사용자 문자열 표현 테스트"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        self.assertEqual(str(user), 'test@example.com')


class UserSerializerTestCase(TestCase):
    """사용자 시리얼라이저 테스트"""
    
    def test_user_registration_serializer_valid_data(self):
        """회원가입 시리얼라이저 유효한 데이터 테스트"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'username': 'testuser'
        }
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
    
    def test_user_registration_serializer_password_mismatch(self):
        """비밀번호 불일치 테스트"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'password_confirm': 'differentpass',
            'username': 'testuser'
        }
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
    
    def test_user_registration_serializer_invalid_email(self):
        """잘못된 이메일 형식 테스트"""
        data = {
            'email': 'invalid-email',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'username': 'testuser'
        }
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_user_serializer(self):
        """사용자 시리얼라이저 테스트"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        serializer = UserSerializer(user)
        data = serializer.data
        
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['username'], 'testuser')
        self.assertNotIn('password', data)  # 비밀번호는 포함되지 않아야 함


class UserAPITestCase(APITestCase):
    """사용자 API 테스트"""
    
    def test_user_registration(self):
        """회원가입 API 테스트"""
        url = reverse('users:register')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'username': 'testuser'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 사용자가 실제로 생성되었는지 확인
        self.assertTrue(User.objects.filter(email='test@example.com').exists())
        
        # 응답에 JWT 토큰이 포함되어 있는지 확인
        response_data = response.json()
        self.assertIn('access', response_data)
        self.assertIn('refresh', response_data)
        self.assertIn('user', response_data)

    def test_login_returns_nickname_required_flag(self):
        """로그인 시 닉네임 필요 플래그 반환 테스트"""
        user = User.objects.create_user(
            email='flag@example.com', password='flagpass123', username='flaguser'
        )
        # 닉네임 미설정 상태 보장
        user.nickname = None
        user.save()

        url = reverse('users:login')
        data = {'email': 'flag@example.com', 'password': 'flagpass123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertIn('nickname_required', body)
        self.assertTrue(body['nickname_required'])

    def test_login_returns_nickname_required_false_when_nickname_exists(self):
        """닉네임이 있는 경우 로그인 시 플래그가 false"""
        user = User.objects.create_user(
            email='hasnick@example.com', password='nickpass123', username='hasnick'
        )
        user.nickname = 'already_set'
        user.save()

        url = reverse('users:login')
        data = {'email': 'hasnick@example.com', 'password': 'nickpass123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertIn('nickname_required', body)
        self.assertFalse(body['nickname_required'])

    def test_set_nickname_immediately_after_registration(self):
        """회원가입 직후 닉네임 설정 플로우 테스트"""
        # 1) 회원가입하여 토큰 수령
        register_url = reverse('users:register')
        register_data = {
            'email': 'flow@example.com',
            'password': 'flowpass123',
            'password_confirm': 'flowpass123',
            'username': 'flowuser'
        }
        register_response = self.client.post(register_url, register_data)
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        tokens = register_response.json()
        access_token = tokens['access']

        # 2) 닉네임 설정 호출
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        nickname_url = reverse('users:nickname')
        nickname_response = self.client.put(nickname_url, {'nickname': 'flow_nick'})
        self.assertEqual(nickname_response.status_code, status.HTTP_200_OK)
        self.assertEqual(nickname_response.json()['nickname'], 'flow_nick')

        # 3) 프로필에서 닉네임 반영 확인
        profile_url = reverse('users:profile')
        profile_response = self.client.get(profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.json()['nickname'], 'flow_nick')
    
    def test_user_registration_duplicate_email(self):
        """중복 이메일 회원가입 테스트"""
        # 먼저 사용자 생성
        User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='existing_user'
        )
        
        url = reverse('users:register')
        data = {
            'email': 'test@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'username': 'new_user'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login(self):
        """로그인 API 테스트"""
        # 테스트 사용자 생성
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        url = reverse('users:login')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIn('access', response_data)
        self.assertIn('refresh', response_data)
        # TokenObtainPairView는 user 정보를 포함하지 않음
    
    def test_user_login_invalid_credentials(self):
        """잘못된 로그인 정보 테스트"""
        url = reverse('users:login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_profile(self):
        """사용자 프로필 조회 테스트"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        # JWT 토큰 생성 및 인증 설정
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('users:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['email'], 'test@example.com')
        self.assertEqual(response_data['username'], 'testuser')
    
    def test_user_profile_unauthorized(self):
        """인증되지 않은 프로필 접근 테스트"""
        url = reverse('users:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh(self):
        """토큰 갱신 테스트"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        refresh = RefreshToken.for_user(user)
        refresh_token = str(refresh)
        
        url = reverse('users:token-refresh')
        data = {'refresh': refresh_token}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIn('access', response_data)


class UserJWTTestCase(TestCase):
    """JWT 토큰 관련 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
    
    def test_jwt_token_generation(self):
        """JWT 토큰 생성 테스트"""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)
        self.assertNotEqual(access_token, refresh_token)
    
    def test_jwt_token_payload(self):
        """JWT 토큰 페이로드 테스트"""
        refresh = RefreshToken.for_user(self.user)
        
        # 토큰에 사용자 ID가 포함되어 있는지 확인
        self.assertEqual(refresh['user_id'], self.user.id)
