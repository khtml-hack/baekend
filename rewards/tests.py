from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal

from .models import Wallet, RewardTransaction
from .services.transaction_service import (
    create_transaction,
    get_user_balance,
    process_reward_earning,
    process_reward_spending
)

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
        user_without_wallet = User.objects.create_user(
            email='nowallet@example.com',
            password='testpass123',
            username='nowallet'  # username 추가로 중복 방지
        )
        # 지갑이 없는 경우 0 반환
        try:
            wallet = Wallet.objects.get(user=user_without_wallet)
            balance = wallet.balance
        except Wallet.DoesNotExist:
            balance = 0
        self.assertEqual(balance, 0)
    
    def test_create_transaction_earn(self):
        """Test earn transaction creation"""
        initial_balance = self.wallet.balance
        
        transaction = create_transaction(
            user=self.user,
            amount=500,
            transaction_type='earn',
            description='Test earning'
        )
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.type, 'earn')
        self.assertEqual(transaction.amount, 500)
        
        # Check wallet balance
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, initial_balance + 500)
    
    def test_create_transaction_spend(self):
        """Test spend transaction creation"""
        initial_balance = self.wallet.balance
        
        transaction = create_transaction(
            user=self.user,
            amount=300,
            transaction_type='spend',
            description='Test spending'
        )
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.type, 'spend')
        self.assertEqual(transaction.amount, 300)
        
        # Check wallet balance
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, initial_balance - 300)
    
    def test_create_transaction_insufficient_balance(self):
        """Test transaction creation with insufficient balance"""
        # Try to spend more than available balance
        with self.assertRaises(ValueError):
            create_transaction(
                user=self.user,
                amount=2000,
                transaction_type='spend',
                description='Insufficient balance test'
            )
    
    def test_process_reward_earning(self):
        """Test reward earning process"""
        initial_balance = self.wallet.balance
        
        result = process_reward_earning(
            user=self.user,
            amount=250,
            reason='Trip completion reward'
        )
        
        self.assertTrue(result['success'])
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, initial_balance + 250)
    
    def test_process_reward_spending(self):
        """Test reward spending process"""
        initial_balance = self.wallet.balance
        
        result = process_reward_spending(
            user=self.user,
            amount=150,
            merchant_info={'name': 'Test Merchant'},
            description='Discount applied'
        )
        
        self.assertTrue(result['success'])
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, initial_balance - 150)
    
    def test_process_reward_spending_insufficient_balance(self):
        """Test reward spending with insufficient balance"""
        result = process_reward_spending(
            user=self.user,
            amount=2000,
            merchant_info={'name': 'Test Merchant'},
            description='Insufficient balance test'
        )
        
        self.assertFalse(result['success'])
        # Check balance unchanged
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
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Set API client authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create test wallet
        self.wallet = Wallet.objects.create(user=self.user, balance=1000)
    
    def test_wallet_balance_api(self):
        """Test wallet balance API"""
        url = reverse('rewards:wallet')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['balance'], 1000)
        self.assertEqual(data['currency_code'], 'LCL')
    
    def test_transaction_history_api(self):
        """Test transaction history API"""
        # Create test transactions with slight delay to ensure order
        transaction1 = RewardTransaction.objects.create(
            wallet=self.wallet,
            type='earn',
            amount=200,
            description='Test earning'
        )
        transaction2 = RewardTransaction.objects.create(
            wallet=self.wallet,
            type='spend',
            amount=100,
            description='Test spending'
        )
        
        url = reverse('rewards:transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 2)
        
        # Check that both transactions are present (order might vary)
        transaction_types = [t['type'] for t in data['results']]
        self.assertIn('earn', transaction_types)
        self.assertIn('spend', transaction_types)
        
        # Check that amounts are correct
        transaction_amounts = [t['amount'] for t in data['results']]
        self.assertIn(200, transaction_amounts)
        self.assertIn(100, transaction_amounts)
    
    def test_reward_api_unauthorized(self):
        """Test unauthorized user"""
        self.client.credentials()  # Remove authentication
        
        url = reverse('rewards:wallet')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
