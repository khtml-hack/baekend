from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class SimpleUserTest(TestCase):
    """간단한 사용자 테스트"""
    
    def test_user_creation(self):
        """사용자 생성 테스트"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_str(self):
        """사용자 문자열 표현 테스트"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        self.assertEqual(str(user), 'test@example.com')
