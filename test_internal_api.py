"""
Django 내부에서 API 테스트
"""
import os
import django
import sys

# Django 설정
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

print("=== Django Internal API 테스트 ===\n")

# Django test client 생성
client = Client()

# 1. 사용자 등록 테스트
print("1. 사용자 등록 API 테스트")
register_data = {
    "email": "internal_test@example.com",
    "password": "testpass123",
    "nickname": "내부테스터"
}

response = client.post('/api/users/register/', 
                      data=json.dumps(register_data),
                      content_type='application/json')

print(f"Status Code: {response.status_code}")
if hasattr(response, 'json'):
    print(f"Response: {response.json()}")
else:
    print(f"Response: {response.content.decode()}")

# 2. 로그인 테스트 (JWT 토큰)
print("\n2. JWT 토큰 발급 테스트")
login_data = {
    "email": "internal_test@example.com", 
    "password": "testpass123"
}

response = client.post('/api/users/token/',
                      data=json.dumps(login_data),
                      content_type='application/json')

print(f"Status Code: {response.status_code}")
response_data = None
if hasattr(response, 'json'):
    response_data = response.json()
    print(f"Response: {response_data}")
else:
    try:
        response_data = json.loads(response.content.decode())
        print(f"Response: {response_data}")
    except:
        print(f"Response: {response.content.decode()}")

# 3. 인증 후 추천 API 테스트
if response_data and 'access' in response_data:
    print("\n3. 여행 추천 API 테스트")
    access_token = response_data['access']
    
    recommendation_data = {
        "origin_address": "서울역",
        "destination_address": "강남역", 
        "region_code": "KR"
    }
    
    response = client.post('/api/trips/recommend/',
                          data=json.dumps(recommendation_data),
                          content_type='application/json',
                          HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    print(f"Status Code: {response.status_code}")
    if hasattr(response, 'json'):
        print(f"Response: {response.json()}")
    else:
        try:
            print(f"Response: {json.loads(response.content.decode())}")
        except:
            print(f"Response: {response.content.decode()}")

print("\n=== 테스트 완료 ===")
