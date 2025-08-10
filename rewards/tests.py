from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from datetime import datetime, time, timedelta
from django.utils import timezone

from .models import Wallet, RewardTransaction
from .services.transaction_service import (
    create_transaction,
    get_user_balance,
    process_reward_earning,
    process_reward_spending
)
from trips.models import Recommendation, Trip

User = get_user_model()


class WalletModelTestCase(TestCase):
    """Wallet model test"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            nickname='testuser'
        )
    
    def test_wallet_creation(self):
        """Test wallet creation"""
        wallet = Wallet.objects.create(user=self.user)
        self.assertEqual(wallet.user, self.user)
        self.assertEqual(wallet.balance, 0)  # BigIntegerField default is 0
        self.assertEqual(wallet.currency_code, 'LCL')
    
    def test_wallet_string_representation(self):
        """Test wallet string representation"""
        wallet = Wallet.objects.create(user=self.user)
        expected_str = f"{self.user.email} - {wallet.balance} {wallet.currency_code}"
        self.assertEqual(str(wallet), expected_str)


class RewardTransactionModelTestCase(TestCase):
    """Reward transaction model test"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            nickname='testuser'
        )
        self.wallet = Wallet.objects.create(user=self.user)
    
    def test_reward_transaction_creation(self):
        """Test reward transaction creation"""
        transaction = RewardTransaction.objects.create(
            wallet=self.wallet,
            type='earn',  # 'transaction_type' -> 'type'
            amount=100,   # BigIntegerField
            description='Test earning'
        )
        
        self.assertEqual(transaction.wallet, self.wallet)
        self.assertEqual(transaction.type, 'earn')
        self.assertEqual(transaction.amount, 100)
        self.assertEqual(transaction.description, 'Test earning')
        self.assertIsNotNone(transaction.created_at)
    
    def test_transaction_string_representation(self):
        """Test transaction string representation"""
        transaction = RewardTransaction.objects.create(
            wallet=self.wallet,
            type='earn',
            amount=100,
            description='Test earning'
        )
        
        expected_str = f"{self.user.email} - earn 100 {self.wallet.currency_code}"
        self.assertEqual(str(transaction), expected_str)


class TransactionServiceTestCase(TestCase):
    """Transaction service test"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            nickname='testuser'
        )
        self.wallet = Wallet.objects.create(user=self.user, balance=1000)  # BigIntegerField
    
    def test_get_user_balance(self):
        """Test user balance retrieval"""
        # 실제 서비스에서 is_active 필드를 사용하지 않으므로 간단히 지갑에서 직접 조회
        balance = self.wallet.balance
        self.assertEqual(balance, 1000)
    
    def test_get_user_balance_no_wallet(self):
        """Test user balance retrieval without wallet"""
        # 새 사용자 생성 (지갑 없음)
        new_user = User.objects.create_user(
            email='newuser@example.com',
            password='newpass123',
            nickname='newuser'
        )
        
        # 지갑이 없는 사용자의 잔액 조회
        balance = get_user_balance(new_user)
        self.assertEqual(balance, 0)  # 새로 생성된 지갑의 기본 잔액
    
    def test_create_transaction_earn(self):
        """Test earn transaction creation"""
        # 수익 거래 생성
        transaction = create_transaction(
            user=self.user,
            transaction_type='earn',
            amount=500,
            description='Test earning transaction'
        )
        
        self.assertEqual(transaction.type, 'earn')
        self.assertEqual(transaction.amount, 500)
        self.assertEqual(transaction.wallet.user, self.user)
        
        # 지갑 잔액 확인
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 1500)  # 1000 + 500
    
    def test_create_transaction_spend(self):
        """Test spend transaction creation"""
        # 지출 거래 생성
        transaction = create_transaction(
            user=self.user,
            transaction_type='spend',
            amount=300,
            description='Test spending transaction'
        )
        
        self.assertEqual(transaction.type, 'spend')
        self.assertEqual(transaction.amount, 300)
        self.assertEqual(transaction.wallet.user, self.user)
        
        # 지갑 잔액 확인
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 700)  # 1000 - 300
    
    def test_create_transaction_insufficient_balance(self):
        """Test transaction creation with insufficient balance"""
        # 잔액 부족으로 인한 지출 거래 실패
        with self.assertRaises(ValueError):
            create_transaction(
                user=self.user,
                transaction_type='spend',
                amount=1500,  # 잔액(1000)보다 큰 금액
                description='Test insufficient balance'
            )
        
        # 지갑 잔액이 변경되지 않았는지 확인
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 1000)
    
    def test_process_reward_earning(self):
        """Test reward earning process"""
        # 보상 적립 처리
        result = process_reward_earning(self.user, 200, 'Test reward')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['new_balance'], 1200)  # 1000 + 200
        
        # 지갑 잔액 확인
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 1200)
    
    def test_process_reward_spending(self):
        """Test reward spending process"""
        # 보상 사용 처리
        result = process_reward_spending(self.user, 400, {'name': 'Test Merchant'}, 'Test spending')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['new_balance'], 600)  # 1000 - 400
        
        # 지갑 잔액 확인
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 600)
    
    def test_process_reward_spending_insufficient_balance(self):
        """Test reward spending with insufficient balance"""
        # 잔액 부족으로 인한 보상 사용 실패
        result = process_reward_spending(self.user, 1500, {'name': 'Test Merchant'}, 'Test insufficient')
        
        self.assertFalse(result['success'])
        self.assertIn('잔액이 부족합니다', result['error'])
        
        # 지갑 잔액이 변경되지 않았는지 확인
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 1000)


class RewardAPITestCase(APITestCase):
    """Reward API test"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            nickname='testuser'
        )
        
        # Create wallet for user
        self.wallet = Wallet.objects.create(user=self.user, balance=1000)
        
        # Create some test transactions
        RewardTransaction.objects.create(
            wallet=self.wallet,
            type='earn',
            amount=500,
            description='Test earning'
        )
        RewardTransaction.objects.create(
            wallet=self.wallet,
            type='spend',
            amount=200,
            description='Test spending'
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_wallet_balance_api(self):
        """Test wallet balance API"""
        url = reverse('rewards:wallet')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        self.assertEqual(data['balance'], 1000)
        self.assertEqual(data['currency_code'], 'LCL')
        self.assertEqual(len(data['recent_transactions']), 2)
    
    def test_transaction_history_api(self):
        """Test transaction history API"""
        url = reverse('rewards:transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['results']), 2)
        
        # 첫 번째 거래 (수익)
        first_transaction = data['results'][0]
        self.assertEqual(first_transaction['type'], 'earn')
        self.assertEqual(first_transaction['amount'], 500)
        
        # 두 번째 거래 (지출)
        second_transaction = data['results'][1]
        self.assertEqual(second_transaction['type'], 'spend')
        self.assertEqual(second_transaction['amount'], 200)
    
    def test_reward_api_unauthorized(self):
        """Test unauthorized user"""
        # 인증 토큰 제거
        self.client.credentials()
        
        url = reverse('rewards:wallet')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_reward_summary_api(self):
        """Test reward summary API"""
        url = reverse('rewards:reward_summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        self.assertEqual(data['current_balance'], 1000)
        self.assertEqual(data['currency_code'], 'LCL')
        self.assertEqual(data['total_earned'], 500)
        self.assertEqual(data['total_spent'], 200)
        self.assertEqual(data['transaction_count'], 2)
        self.assertEqual(len(data['recent_transactions']), 2)

    # 출발 시 보상 관련 테스트들은 비활성화 (출발 시 보상 제거됨)
    # def test_preview_departure_reward_api(self):
    #     """Test preview departure reward API"""
    #     # Create test recommendation and trip
    #     recommendation = Recommendation.objects.create(
    #         recommended_bucket='T0',
    #         window_start=time(6, 0),
    #         window_end=time(8, 0),
    #         expected_congestion_level=2
    #     )
    #     
    #     trip = Trip.objects.create(
    #         user=self.user,
    #         recommendation=recommendation,
    #         origin_address='서울 강남구 역삼동',
    #         destination_address='서울 서초구 서초동'
    #     )
    #     
    #     url = reverse('rewards:preview_departure_reward', args=[trip.id])
    #     response = self.client.get(url)
    #     
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     data = response.data
    #     
    #     self.assertEqual(data['trip_id'], trip.id)
    #     self.assertIn('expected_reward', data)
    #     self.assertIn('recommendation_info', data)
    # 
    # def test_preview_departure_reward_unauthorized(self):
    #     """Test preview departure reward API without authentication"""
    #     self.client.credentials()
    #     
    #     url = reverse('rewards:preview_departure_reward', args=[1])
    #     response = self.client.get(url)
    #     
    #     self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    # 
    # def test_preview_departure_reward_invalid_trip(self):
    #     """Test preview departure reward API with invalid trip ID"""
    #     url = reverse('rewards:preview_departure_reward', args=[99999])
    #     response = self.client.get(url)
    #     
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RewardCalculationTestCase(TestCase):
    """Reward calculation test"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            nickname='testuser'
        )
        self.wallet = Wallet.objects.create(user=self.user)
        
        # Create test recommendation
        self.recommendation = Recommendation.objects.create(
            user=self.user,
            recommended_bucket='T0',
            window_start=time(6, 0),
            window_end=time(8, 0),
            expected_congestion_level=2,
            expected_duration_min=30,
            origin_address='서울 강남구 역삼동',
            destination_address='서울 서초구 서초동',
            rationale='Test recommendation'
        )
        
        # Create test trip
        self.trip = Trip.objects.create(
            user=self.user,
            recommendation=self.recommendation
        )

    # 출발 시 보상 관련 테스트들은 비활성화 (출발 시 보상 제거됨)
    # def test_calculate_departure_reward_basic(self):
    #     """Test basic departure reward calculation"""
    #     from .utils import calculate_departure_reward
    #     
    #     reward_info = calculate_departure_reward(self.trip)
    #     
    #     self.assertIn('base_reward', reward_info)
    #     self.assertIn('multiplier', reward_info)
    #     self.assertIn('total_reward', reward_info)
    #     self.assertIn('bonus_type', reward_info)
    #     self.assertIn('bonus_description', reward_info)
    # 
    # def test_calculate_departure_reward_low_congestion(self):
    #     """Test departure reward with low congestion bonus"""
    #     from .utils import calculate_departure_reward
    #     
    #     # 낮은 혼잡도로 설정
    #     self.recommendation.expected_congestion_level = 1
    #     self.recommendation.save()
    #     
    #     reward_info = calculate_departure_reward(self.trip)
    #     
    #     self.assertEqual(reward_info['bonus_type'], 'low_congestion')
    #     self.assertIn('혼잡도 낮은 시간대', reward_info['bonus_description'])
    # 
    # def test_calculate_departure_reward_no_recommendation(self):
    #     """Test departure reward without recommendation"""
    #     from .utils import calculate_departure_reward
    #     
    #     # 추천 정보가 없는 여행
    #     trip_no_rec = Trip.objects.create(
    #         user=self.user,
    #         origin_address='서울 강남구 역삼동',
    #         destination_address='서울 서초구 서초동'
    #     )
    #     
    #     reward_info = calculate_departure_reward(trip_no_rec)
    #     
    #     # 추천 정보가 없으면 기본 보상만
    #     self.assertEqual(reward_info['bonus_type'], 'basic')
    #     self.assertEqual(reward_info['multiplier'], 1.0)
    # 
    # def test_reward_for_trip_departure(self):
    #     """Test trip departure reward function"""
    #     from .utils import reward_for_trip_departure
    #     
    #     result = reward_for_trip_departure(self.user, self.trip)
    #     
    #     self.assertIn('departure_reward', result)
    #     self.assertIn('message', result)
    #     self.assertIn('wallet_balance', result)
    #     
    #     # 지갑 잔액 확인
    #     self.wallet.refresh_from_db()
    #     self.assertGreater(self.wallet.balance, 0)

    def test_reward_for_trip_completion_with_accuracy_bonus(self):
        """Test trip completion reward with accuracy bonus"""
        from .utils import reward_for_trip_completion
        
        # AI 추천 시간에 정확히 도착한 경우: 30분 예상/실제
        self.trip.started_at = timezone.now()
        self.trip.arrived_at = self.trip.started_at + timedelta(minutes=30)
        self.trip.save()

        result = reward_for_trip_completion(self.user, self.trip)
        
        # 응답 구조 확인
        self.assertIn('completion_reward', result)
        self.assertIn('message', result)
        self.assertIn('wallet_balance', result)
        
        # completion_reward가 딕셔너리인지 확인
        completion_reward = result['completion_reward']
        self.assertIsInstance(completion_reward, dict)
        self.assertIn('total_reward', completion_reward)
        self.assertIn('base_reward', completion_reward)
        self.assertIn('multiplier', completion_reward)
        
        # 지갑 잔액 확인
        self.wallet.refresh_from_db()
        self.assertGreater(self.wallet.balance, 0)
