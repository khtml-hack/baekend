import requests
import json

# 서버 URL
BASE_URL = "http://127.0.0.1:8000/api"

print("=== Django REST API 테스트 ===\n")

# 1. 사용자 등록 테스트
print("1. 사용자 등록 테스트")
register_data = {
    "email": "api_test@example.com",
    "password": "testpass123",
    "nickname": "API테스터"
}

try:
    response = requests.post(f"{BASE_URL}/users/register/", json=register_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 201:
        print("✅ 사용자 등록 성공!")
    else:
        print("❌ 사용자 등록 실패")
except Exception as e:
    print(f"오류: {e}")

print("\n" + "="*50 + "\n")

# 2. 로그인 테스트
print("2. 로그인 테스트")
login_data = {
    "email": "api_test@example.com",
    "password": "testpass123"
}

try:
    response = requests.post(f"{BASE_URL}/users/login/", json=login_data)
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {response_data}")
    
    if response.status_code == 200:
        print("✅ 로그인 성공!")
        access_token = response_data.get('access')
        refresh_token = response_data.get('refresh')
        
        # 3. 인증이 필요한 API 테스트 (여행 추천)
        print("\n" + "="*50 + "\n")
        print("3. 여행 추천 API 테스트")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        recommendation_data = {
            "origin_address": "서울역",
            "destination_address": "강남역",
            "region_code": "KR"
        }
        
        response = requests.post(f"{BASE_URL}/trips/recommendations/", 
                               json=recommendation_data, 
                               headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ 여행 추천 성공!")
        else:
            print("❌ 여행 추천 실패")
            
    else:
        print("❌ 로그인 실패")
except Exception as e:
    print(f"오류: {e}")

print("\n=== API 테스트 완료 ===")
