from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import datetime
from unittest.mock import patch

from .utils import (
    validate_korean_phone_number,
    format_phone_number,
    calculate_age_from_korean_id,
    mask_personal_info,
    get_time_greeting,
    safe_divide,
    truncate_text,
    parse_boolean
)
from .exceptions import (
    BaseAppException,
    ValidationException,
    BusinessLogicException,
    ExternalAPIException,
    DataNotFoundException,
    PermissionDeniedException
)


class PhoneNumberUtilsTestCase(TestCase):
    """전화번호 관련 유틸리티 테스트"""
    
    def test_validate_korean_phone_number_valid(self):
        """유효한 한국 전화번호 검증 테스트"""
        valid_numbers = [
            '010-1234-5678',
            '01012345678',
            '010 1234 5678',
            '02-123-4567',
            '02-1234-5678',
            '031-123-4567',
            '070-1234-5678',
            '080-123-4567'
        ]
        
        for number in valid_numbers:
            with self.subTest(number=number):
                self.assertTrue(validate_korean_phone_number(number))
    
    def test_validate_korean_phone_number_invalid(self):
        """유효하지 않은 전화번호 검증 테스트"""
        invalid_numbers = [
            '',
            '123-456-7890',
            '010-123-456',
            '011-1234-5678',  # 011은 더 이상 사용되지 않음
            '010-12345-6789',  # 자릿수 초과
            'abc-defg-hijk',
            '02-12-3456'  # 자릿수 부족
        ]
        
        for number in invalid_numbers:
            with self.subTest(number=number):
                self.assertFalse(validate_korean_phone_number(number))
    
    def test_format_phone_number_success(self):
        """전화번호 포맷팅 성공 테스트"""
        test_cases = [
            ('01012345678', '010-1234-5678'),
            ('010-1234-5678', '010-1234-5678'),
            ('010 1234 5678', '010-1234-5678'),
            ('021234567', '02-123-4567'),
            ('0212345678', '02-1234-5678'),
            ('07012345678', '070-1234-5678')
        ]
        
        for input_number, expected in test_cases:
            with self.subTest(input_number=input_number):
                result = format_phone_number(input_number)
                self.assertEqual(result, expected)
    
    def test_format_phone_number_invalid(self):
        """유효하지 않은 전화번호 포맷팅 시 예외 발생 테스트"""
        invalid_numbers = ['123-456-7890', '', 'invalid']
        
        for number in invalid_numbers:
            with self.subTest(number=number):
                with self.assertRaises(ValidationError):
                    format_phone_number(number)


class PersonalInfoUtilsTestCase(TestCase):
    """개인정보 관련 유틸리티 테스트"""
    
    def test_calculate_age_from_korean_id_valid(self):
        """주민등록번호에서 나이 계산 테스트"""
        # 2024년 기준으로 테스트 (현재 시점에 따라 조정 필요)
        test_cases = [
            ('900101-1234567', 34),  # 1990년생 남성
            ('850315-2345678', 39),  # 1985년생 여성
            ('050101-3123456', 19),  # 2005년생 남성
            ('030601-4234567', 21),  # 2003년생 여성
        ]
        
        with patch('common.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 6, 15)
            
            for resident_id, expected_age in test_cases:
                with self.subTest(resident_id=resident_id):
                    age = calculate_age_from_korean_id(resident_id)
                    self.assertEqual(age, expected_age)
    
    def test_calculate_age_from_korean_id_invalid(self):
        """유효하지 않은 주민등록번호 처리 테스트"""
        invalid_ids = [
            '',
            '123456',  # 너무 짧음
            '900101-5123456',  # 유효하지 않은 성별코드
            'abcdef-1234567',  # 숫자가 아님
            None
        ]
        
        for resident_id in invalid_ids:
            with self.subTest(resident_id=resident_id):
                age = calculate_age_from_korean_id(resident_id)
                self.assertIsNone(age)
    
    def test_mask_personal_info_phone(self):
        """전화번호 마스킹 테스트"""
        test_cases = [
            ('010-1234-5678', '010-****-5678'),
            ('01012345678', '010****5678'),
            ('02-123-4567', '02-****-4567')
        ]
        
        for phone, expected in test_cases:
            with self.subTest(phone=phone):
                result = mask_personal_info(phone, 'phone')
                self.assertEqual(result, expected)
    
    def test_mask_personal_info_email(self):
        """이메일 마스킹 테스트"""
        test_cases = [
            ('test@example.com', 'tes*@example.com'),
            ('hello@gmail.com', 'hel**@gmail.com'),
            ('ab@test.com', 'a*@test.com')
        ]
        
        for email, expected in test_cases:
            with self.subTest(email=email):
                result = mask_personal_info(email, 'email')
                self.assertEqual(result, expected)
    
    def test_mask_personal_info_name(self):
        """이름 마스킹 테스트"""
        test_cases = [
            ('김철수', '김*수'),
            ('이영희', '이*희'),
            ('박정', '박*'),
            ('최민수정', '최**정')
        ]
        
        for name, expected in test_cases:
            with self.subTest(name=name):
                result = mask_personal_info(name, 'name')
                self.assertEqual(result, expected)


class GeneralUtilsTestCase(TestCase):
    """일반 유틸리티 함수 테스트"""
    
    @patch('common.utils.datetime')
    def test_get_time_greeting(self, mock_datetime):
        """시간대별 인사말 테스트"""
        test_cases = [
            (8, "좋은 아침입니다"),
            (14, "좋은 오후입니다"),
            (19, "좋은 저녁입니다"),
            (23, "안녕하세요"),
            (2, "안녕하세요")
        ]
        
        for hour, expected_greeting in test_cases:
            with self.subTest(hour=hour):
                mock_datetime.now.return_value = datetime(2024, 1, 1, hour, 0, 0)
                greeting = get_time_greeting()
                self.assertEqual(greeting, expected_greeting)
    
    def test_safe_divide(self):
        """안전한 나눗셈 테스트"""
        test_cases = [
            (10, 2, 5.0),
            (10, 0, 0.0),  # 기본값
            (10, 0, -1.0),  # 사용자 정의 기본값
            (7, 3, 7/3),
            (0, 5, 0.0)
        ]
        
        for numerator, denominator, expected in test_cases:
            with self.subTest(numerator=numerator, denominator=denominator):
                if expected == -1.0:  # 사용자 정의 기본값 테스트
                    result = safe_divide(numerator, denominator, default=-1.0)
                else:
                    result = safe_divide(numerator, denominator)
                self.assertEqual(result, expected)
    
    def test_safe_divide_invalid_input(self):
        """잘못된 입력에 대한 안전한 나눗셈 테스트"""
        result = safe_divide("invalid", 2, default=99.0)
        self.assertEqual(result, 99.0)
    
    def test_truncate_text(self):
        """텍스트 자르기 테스트"""
        test_cases = [
            ("안녕하세요", 5, "안녕하세요"),  # 길이 이내
            ("안녕하세요 반갑습니다", 7, "안녕하세..."),  # 자르기
            ("Hello World", 8, "Hello..."),
            ("", 10, ""),  # 빈 문자열
            ("Short", 20, "Short"),  # 짧은 문자열
            ("Custom suffix", 10, "Custom ***", "***")  # 사용자 정의 suffix
        ]
        
        for text, max_length, expected, *args in test_cases:
            with self.subTest(text=text, max_length=max_length):
                if args:  # suffix 인자가 있는 경우
                    result = truncate_text(text, max_length, suffix=args[0])
                else:
                    result = truncate_text(text, max_length)
                self.assertEqual(result, expected)
    
    def test_parse_boolean(self):
        """Boolean 파싱 테스트"""
        test_cases = [
            (True, True),
            (False, False),
            ("true", True),
            ("TRUE", True),
            ("false", False),
            ("FALSE", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            ("on", True),
            ("off", False),
            (1, True),
            (0, False),
            (None, False),
            ("invalid", False),
            ([], False)
        ]
        
        for value, expected in test_cases:
            with self.subTest(value=value):
                result = parse_boolean(value)
                self.assertEqual(result, expected)


class ExceptionTestCase(TestCase):
    """예외 클래스 테스트"""
    
    def test_base_app_exception(self):
        """기본 앱 예외 테스트"""
        message = "테스트 예외"
        error_code = "TEST_001"
        
        exception = BaseAppException(message, error_code)
        
        self.assertEqual(str(exception), message)
        self.assertEqual(exception.message, message)
        self.assertEqual(exception.error_code, error_code)
    
    def test_validation_exception(self):
        """유효성 검증 예외 테스트"""
        message = "유효성 검증 실패"
        
        exception = ValidationException(message)
        
        self.assertEqual(str(exception), message)
        self.assertIsInstance(exception, BaseAppException)
    
    def test_business_logic_exception(self):
        """비즈니스 로직 예외 테스트"""
        message = "비즈니스 로직 오류"
        
        exception = BusinessLogicException(message)
        
        self.assertEqual(str(exception), message)
        self.assertIsInstance(exception, BaseAppException)
    
    def test_external_api_exception(self):
        """외부 API 예외 테스트"""
        message = "API 호출 실패"
        api_name = "kakao"
        status_code = 500
        
        exception = ExternalAPIException(message, api_name, status_code)
        
        self.assertEqual(str(exception), message)
        self.assertEqual(exception.api_name, api_name)
        self.assertEqual(exception.status_code, status_code)
        self.assertIsInstance(exception, BaseAppException)
    
    def test_data_not_found_exception(self):
        """데이터 없음 예외 테스트"""
        message = "데이터를 찾을 수 없습니다"
        
        exception = DataNotFoundException(message)
        
        self.assertEqual(str(exception), message)
        self.assertIsInstance(exception, BaseAppException)
    
    def test_permission_denied_exception(self):
        """권한 거부 예외 테스트"""
        message = "접근 권한이 없습니다"
        
        exception = PermissionDeniedException(message)
        
        self.assertEqual(str(exception), message)
        self.assertIsInstance(exception, BaseAppException)


class CommonIntegrationTestCase(TestCase):
    """공통 기능 통합 테스트"""
    
    def test_phone_validation_and_formatting_workflow(self):
        """전화번호 검증 및 포맷팅 워크플로우 테스트"""
        raw_phone = "01012345678"
        
        # 1. 유효성 검증
        is_valid = validate_korean_phone_number(raw_phone)
        self.assertTrue(is_valid)
        
        # 2. 포맷팅
        formatted = format_phone_number(raw_phone)
        self.assertEqual(formatted, "010-1234-5678")
        
        # 3. 마스킹
        masked = mask_personal_info(formatted, 'phone')
        self.assertEqual(masked, "010-****-5678")
    
    def test_exception_hierarchy(self):
        """예외 클래스 계층 구조 테스트"""
        exceptions = [
            ValidationException("test"),
            BusinessLogicException("test"),
            ExternalAPIException("test"),
            DataNotFoundException("test"),
            PermissionDeniedException("test")
        ]
        
        for exc in exceptions:
            self.assertIsInstance(exc, BaseAppException)
            self.assertIsInstance(exc, Exception)
