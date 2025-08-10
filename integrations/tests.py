from django.test import TestCase
from django.conf import settings
from unittest.mock import patch, Mock, MagicMock
import json

from .kakao import address_search, keyword_search, category_search, search_address
from .openai_gpt import chat_json, get_travel_recommendation


class KakaoAPITestCase(TestCase):
    """Kakao API 통합 테스트"""

    def setUp(self):
        self.mock_kakao_address_response = {
            "meta": {"total_count": 1, "pageable_count": 1, "is_end": True},
            "documents": [
                {
                    "address_name": "서울 강남구 역삼동 123-45",
                    "x": "127.0276368",
                    "y": "37.4979462",
                    "address": {
                        "region_1depth_name": "서울",
                        "region_2depth_name": "강남구",
                        "region_3depth_name": "역삼동"
                    }
                }
            ]
        }
        
        self.mock_kakao_keyword_response = {
            "meta": {"total_count": 2, "pageable_count": 2, "is_end": True},
            "documents": [
                {
                    "place_name": "스타벅스 역삼점",
                    "category_name": "음식점 > 카페",
                    "phone": "02-123-4567",
                    "address_name": "서울 강남구 역삼동",
                    "x": "127.0276368",
                    "y": "37.4979462"
                }
            ]
        }
        
        self.mock_kakao_category_response = {
            "meta": {"total_count": 3, "pageable_count": 3, "is_end": True},
            "documents": [
                {
                    "place_name": "맛있는 식당",
                    "category_name": "음식점 > 한식",
                    "phone": "02-987-6543",
                    "address_name": "서울 강남구 역삼동",
                    "x": "127.0276368",
                    "y": "37.4979462",
                    "distance": "500"
                }
            ]
        }

    @patch('integrations.kakao.requests.get')
    def test_address_search_success(self, mock_get):
        """주소 검색 API 성공 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = self.mock_kakao_address_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.settings(KAKAO_API_KEY='test_api_key'):
            result = address_search("서울 강남구 역삼동")
            
        self.assertEqual(result['documents'][0]['address_name'], "서울 강남구 역삼동 123-45")
        self.assertEqual(result['meta']['total_count'], 1)
        mock_get.assert_called_once()

    def test_address_search_no_api_key(self):
        """API 키가 없을 때 예외 발생 테스트"""
        with self.settings(KAKAO_API_KEY=None):
            with self.assertRaises(ValueError) as context:
                address_search("서울 강남구")
            
        self.assertIn("KAKAO_API_KEY가 설정되지 않았습니다", str(context.exception))

    @patch('integrations.kakao.requests.get')
    def test_keyword_search_success(self, mock_get):
        """키워드 검색 API 성공 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = self.mock_kakao_keyword_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.settings(KAKAO_API_KEY='test_api_key'):
            result = keyword_search("스타벅스", x=127.0276368, y=37.4979462)
            
        self.assertEqual(result['documents'][0]['place_name'], "스타벅스 역삼점")
        mock_get.assert_called_once()

    @patch('integrations.kakao.requests.get')
    def test_keyword_search_without_coordinates(self, mock_get):
        """좌표 없이 키워드 검색 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = self.mock_kakao_keyword_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.settings(KAKAO_API_KEY='test_api_key'):
            result = keyword_search("스타벅스")
            
        self.assertEqual(result['documents'][0]['place_name'], "스타벅스 역삼점")
        # 좌표 매개변수가 params에 포함되지 않았는지 확인
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertNotIn('x', params)
        self.assertNotIn('y', params)

    @patch('integrations.kakao.requests.get')
    def test_category_search_success(self, mock_get):
        """카테고리 검색 API 성공 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = self.mock_kakao_category_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.settings(KAKAO_API_KEY='test_api_key'):
            result = category_search(37.4979462, 127.0276368, code="FD6", radius=1000)
            
        self.assertEqual(result['documents'][0]['place_name'], "맛있는 식당")
        self.assertEqual(result['documents'][0]['distance'], "500")
        mock_get.assert_called_once()

    @patch('integrations.kakao.requests.get')
    def test_search_address_legacy_function(self, mock_get):
        """기존 search_address 함수 테스트 (하위 호환성)"""
        mock_response = Mock()
        mock_response.json.return_value = self.mock_kakao_address_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.settings(KAKAO_API_KEY='test_api_key'):
            result = search_address("서울 강남구 역삼동")
            
        self.assertEqual(result['normalized_address'], "서울 강남구 역삼동 123-45")
        self.assertEqual(result['x'], "127.0276368")
        self.assertEqual(result['y'], "37.4979462")
        self.assertEqual(result['region_1depth_name'], "서울")

    @patch('integrations.kakao.requests.get')
    def test_search_address_no_results(self, mock_get):
        """검색 결과가 없을 때 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = {"meta": {"total_count": 0}, "documents": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.settings(KAKAO_API_KEY='test_api_key'):
            result = search_address("존재하지않는주소")
            
        self.assertEqual(result['normalized_address'], "존재하지않는주소")

    @patch('integrations.kakao.requests.get')
    def test_api_request_exception(self, mock_get):
        """API 요청 실패 시 예외 처리 테스트"""
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("Network error")
        
        with self.settings(KAKAO_API_KEY='test_api_key'):
            with self.assertRaises(Exception) as context:
                address_search("서울 강남구")
                
        self.assertIn("Kakao 주소 검색 API 호출 실패", str(context.exception))


class OpenAIGPTTestCase(TestCase):
    """OpenAI GPT 통합 테스트"""

    def setUp(self):
        self.mock_openai_response = Mock()
        self.mock_openai_response.choices = [
            Mock(message=Mock(content='{"result": "test response"}'))
        ]

    @patch('integrations.openai_gpt.OpenAI')
    def test_chat_json_success(self, mock_openai_class):
        """GPT 채팅 API 성공 테스트"""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = self.mock_openai_response
        mock_openai_class.return_value = mock_client
        
        with self.settings(OPENAI_API_KEY='test_openai_key'):
            result = chat_json(
                system="You are a helpful assistant.",
                user="Hello, how are you?"
            )
            
        self.assertEqual(result, '{"result": "test response"}')
        mock_client.chat.completions.create.assert_called_once()

    def test_chat_json_no_api_key(self):
        """OpenAI API 키가 없을 때 예외 발생 테스트"""
        with self.settings(OPENAI_API_KEY=None):
            with self.assertRaises(ValueError) as context:
                chat_json("system", "user")
                
        self.assertIn("OPENAI_API_KEY가 설정되지 않았습니다", str(context.exception))

    @patch('integrations.openai_gpt.OpenAI')
    def test_get_travel_recommendation_success(self, mock_openai_class):
        """여행 추천 생성 성공 테스트"""
        mock_recommendation_response = Mock()
        mock_recommendation_response.choices = [
            Mock(message=Mock(content='''{
                "recommendations": [
                    {
                        "option_type": "최적 시간",
                        "recommended_bucket": "T0",
                        "recommended_window": {"start": "06:00", "end": "08:00"},
                        "optimal_departure_time": "06:30",
                        "rationale": "테스트 추천 - T0 시간대가 가장 혼잡도가 낮습니다",
                        "expected_duration_min": 30,
                        "expected_congestion_level": 2,
                        "congestion_description": "원활",
                        "time_sensitivity": "보통",
                        "time_saved_min": 20,
                        "reward_amount": 100
                    },
                    {
                        "option_type": "대안 시간",
                        "recommended_bucket": "T1",
                        "recommended_window": {"start": "08:00", "end": "10:00"},
                        "optimal_departure_time": "08:30",
                        "rationale": "테스트 대안 추천",
                        "expected_duration_min": 35,
                        "expected_congestion_level": 3,
                        "congestion_description": "보통",
                        "time_sensitivity": "보통",
                        "time_saved_min": 15,
                        "reward_amount": 80
                    }
                ],
                "current_time_analysis": {
                    "departure_time": "09:41",
                    "arrival_time": "10:31",
                    "duration_min": 50,
                    "congestion_level": 5,
                    "congestion_description": "매우 혼잡"
                }
            }'''))
        ]
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_recommendation_response
        mock_openai_class.return_value = mock_client
        
        current_congestion = {"T0": 2.1, "T1": 1.8, "T2": 3.2, "T3": 2.8}
        full_congestion_data = {"monthly_data": {"01": {"T0": 2.0, "T1": 1.9, "T2": 3.1, "T3": 2.7}}}
        
        with self.settings(OPENAI_API_KEY='test_openai_key'):
            result = get_travel_recommendation(
                "서울 강남구",
                "서울 홍대",
                current_congestion,
                full_congestion_data
            )
            
        # 새로운 응답 구조 검증
        self.assertIsInstance(result, dict)
        self.assertIn('recommendations', result)
        self.assertIn('current_time_analysis', result)
        
        # recommendations 배열 검증
        self.assertEqual(len(result['recommendations']), 2)
        self.assertEqual(result['recommendations'][0]['recommended_bucket'], "T0")
        self.assertEqual(result['recommendations'][0]['option_type'], "최적 시간")
        self.assertEqual(result['recommendations'][1]['option_type'], "대안 시간")
        
        # current_time_analysis 검증
        self.assertEqual(result['current_time_analysis']['departure_time'], "09:41")
        self.assertEqual(result['current_time_analysis']['congestion_level'], 5)
        
        mock_client.chat.completions.create.assert_called_once()

    @patch('integrations.openai_gpt.OpenAI')
    def test_openai_api_exception(self, mock_openai_class):
        """OpenAI API 호출 실패 시 예외 처리 테스트"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_client
        
        with self.settings(OPENAI_API_KEY='test_openai_key'):
            with self.assertRaises(Exception) as context:
                chat_json("system", "user")
                
        self.assertIn("OpenAI API 호출 실패", str(context.exception))


class IntegrationTestCase(TestCase):
    """통합 테스트"""
    
    @patch('integrations.kakao.requests.get')
    @patch('integrations.openai_gpt.OpenAI')
    def test_full_workflow_integration(self, mock_openai_class, mock_requests_get):
        """전체 워크플로우 통합 테스트"""
        # Kakao API 모킹
        mock_kakao_response = Mock()
        mock_kakao_response.json.return_value = {
            "meta": {"total_count": 1},
            "documents": [{
                "address_name": "서울 강남구 역삼동",
                "x": "127.0276368",
                "y": "37.4979462"
            }]
        }
        mock_kakao_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_kakao_response
        
        # OpenAI API 모킹
        mock_openai_response = Mock()
        mock_openai_response.choices = [
            Mock(message=Mock(content='''{
                "recommendations": [
                    {
                        "option_type": "최적 시간",
                        "recommended_bucket": "T0",
                        "recommended_window": {"start": "06:00", "end": "08:00"},
                        "optimal_departure_time": "06:30",
                        "rationale": "테스트 통합 추천",
                        "expected_duration_min": 30,
                        "expected_congestion_level": 2,
                        "congestion_description": "원활",
                        "time_sensitivity": "보통",
                        "time_saved_min": 20,
                        "reward_amount": 100
                    },
                    {
                        "option_type": "대안 시간",
                        "recommended_bucket": "T1",
                        "recommended_window": {"start": "08:00", "end": "10:00"},
                        "optimal_departure_time": "08:30",
                        "rationale": "테스트 통합 대안",
                        "expected_duration_min": 35,
                        "expected_congestion_level": 3,
                        "congestion_description": "보통",
                        "time_sensitivity": "보통",
                        "time_saved_min": 15,
                        "reward_amount": 80
                    }
                ],
                "current_time_analysis": {
                    "departure_time": "09:41",
                    "arrival_time": "10:31",
                    "duration_min": 50,
                    "congestion_level": 5,
                    "congestion_description": "매우 혼잡"
                }
            }'''))
        ]
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai_class.return_value = mock_client
        
        with self.settings(KAKAO_API_KEY='test_kakao_key', OPENAI_API_KEY='test_openai_key'):
            # 1. 주소 검색
            address_result = search_address("서울 강남구")
            
            # 2. 여행 추천 생성
            recommendation_result = get_travel_recommendation(
                "서울 강남구",
                "서울 홍대",
                {"T0": 2.1, "T1": 1.8}
            )
            
        # 결과 검증
        self.assertEqual(address_result['normalized_address'], "서울 강남구 역삼동")
        self.assertIsInstance(recommendation_result, dict)
        self.assertIn('recommendations', recommendation_result)
        self.assertIn('current_time_analysis', recommendation_result)
        
        # recommendations 검증
        self.assertEqual(len(recommendation_result['recommendations']), 2)
        self.assertEqual(recommendation_result['recommendations'][0]['recommended_bucket'], "T0")
        self.assertEqual(recommendation_result['recommendations'][0]['option_type'], "최적 시간")
        
        # current_time_analysis 검증
        self.assertEqual(recommendation_result['current_time_analysis']['departure_time'], "09:41")
        self.assertEqual(recommendation_result['current_time_analysis']['congestion_level'], 5)
        
        # API 호출 횟수 검증
        self.assertEqual(mock_requests_get.call_count, 1)
        mock_client.chat.completions.create.assert_called_once()
