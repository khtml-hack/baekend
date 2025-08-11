# 🚀 API 명세서

> **기본 URL**: `/api/`  
> **인증 방식**: JWT Bearer 토큰 (별도 명시된 경우 제외)  
> **응답 형식**: JSON

---

## 👥 사용자 관리 (Users)

### 🔐 회원가입
**POST** `/api/users/register/`

**요청 본문:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "password_confirm": "password123"
}
```

**응답:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "nickname": null,
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 🔑 로그인
**POST** `/api/users/login/` 또는 `/api/users/token/`

**요청 본문:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**응답:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "nickname_required": true
}
```

### 🔄 토큰 갱신
**POST** `/api/users/token/refresh/`

**요청 본문:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**응답:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 👤 프로필 조회/수정
**GET/PUT** `/api/users/profile/` 또는 `/api/users/me/`

**응답 (GET):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "nickname": "사용자닉네임",
  "date_joined": "2024-01-01T00:00:00Z"
}
```

### ✏️ 닉네임 변경
**PATCH** `/api/users/nickname/`

**요청 본문:**
```json
{
  "nickname": "새로운닉네임"
}
```

**응답:**
```json
{
  "nickname": "새로운닉네임"
}
```

### 🚪 로그아웃
**POST** `/api/users/logout/`

**요청 본문:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

## 📋 프로필 관리 (Profiles)

### ✅ 동의서 저장
**POST** `/api/profiles/consents/`

**요청 본문:**
```json
{
  "consent_type": "marketing",
  "consent_status": true
}
```

**응답:**
```json
{
  "id": 1,
  "consent_type": "marketing",
  "consent_status": true,
  "consented_at": "2024-01-01T00:00:00Z"
}
```

### 🏠 저장된 경로 관리
**GET/POST** `/api/profiles/routes/`

**요청 본문 (POST):**
```json
{
  "route_type": "집",
  "address": "서울시 강남구 테헤란로 123",
  "lat": 37.5665,
  "lng": 126.9780
}
```

**응답 (GET):**
```json
[
  {
    "id": 1,
    "route_type": "집",
    "address": "서울시 강남구 테헤란로 123",
    "lat": 37.5665,
    "lng": 126.9780,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**경로 타입 옵션:**
- `집` - 집
- `직장` - 직장  
- `학교` - 학교

### 🔧 특정 경로 관리
**GET/PUT/PATCH/DELETE** `/api/profiles/routes/<id>/`

---

## 🚗 여행 관리 (Trips)

### 🎯 여행 추천 생성
**POST** `/api/trips/recommend/`

**요청 본문:**
```json
{
  "origin_address": "서울시 강남구",
  "destination_address": "서울시 서초구",
  "region_code": "110000"
}
```

**응답:**
```json
{
  "recommended_bucket": "T1",
  "window_start": "08:00:00",
  "window_end": "10:00:00",
  "expected_duration_min": 45,
  "expected_congestion_level": 3,
  "rationale": "08:00-10:00 시간대는 교통량이 적고 예상 소요시간이 짧습니다."
}
```

**시간대 옵션:**
- `T0` - 06:00~08:00
- `T1` - 08:00~10:00  
- `T2` - 17:00~19:00
- `T3` - 19:00~21:00

### 🚀 여행 시작
**POST** `/api/trips/start/<recommendation_id>/`

**응답:**
```json
{
  "id": 1,
  "status": "ongoing",
  "planned_departure": "2024-01-01T08:00:00Z",
  "started_at": "2024-01-01T08:00:00Z",
  "message": "여행이 시작되었습니다!"
}
```

### 🎉 여행 완료
**POST** `/api/trips/arrive/<trip_id>/`

**응답:**
```json
{
  "id": 1,
  "status": "arrived",
  "arrived_at": "2024-01-01T08:45:00Z",
  "actual_duration_min": 45,
  "completion_reward": 100
}
```

### 📚 여행 히스토리
**GET** `/api/trips/history/`

**응답:**
```json
[
  {
    "id": 1,
    "status": "arrived",
    "origin_address": "서울시 강남구",
    "destination_address": "서울시 서초구",
    "planned_departure": "2024-01-01T08:00:00Z",
    "started_at": "2024-01-01T08:00:00Z",
    "arrived_at": "2024-01-01T08:45:00Z",
    "actual_duration_min": 45,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### ⏰ 최적 출발시간 조회
**GET** `/api/trips/optimal-time/?window_hours=2&current_time=2024-01-01 07:00&location=gangnam`

**쿼리 파라미터:**
- `window_hours` (기본값: 2) - 조회할 시간 범위
- `current_time` (YYYY-MM-DD HH:MM) - 현재 시간
- `location` (예: gangnam) - 지역

**응답:**
```json
{
  "optimal_time": "08:00",
  "alternative_times": ["07:30", "08:30"],
  "search_window": "07:00-09:00",
  "location": "gangnam",
  "precision": "high",
  "analyzed_minutes": 120
}
```

---

## 💰 지갑 관리 (Wallet)

### 💳 지갑 잔액 조회
**GET** `/api/wallet/`

**응답:**
```json
{
  "id": 1,
  "balance": 1500,
  "currency_code": "LCL",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "recent_transactions": [
    {
      "id": 1,
      "type": "earn",
      "amount": 100,
      "description": "여행 완료 보상",
      "created_at": "2024-01-01T08:45:00Z"
    }
  ]
}
```

### 📊 거래 내역 조회
**GET** `/api/wallet/transactions/?page=1&page_size=20`

**쿼리 파라미터:**
- `page` - 페이지 번호
- `page_size` - 페이지 크기

**응답:**
```json
{
  "count": 25,
  "next": "http://api.example.com/api/wallet/transactions/?page=2&page_size=20",
  "previous": null,
  "results": [
    {
      "id": 1,
      "type": "earn",
      "amount": 100,
      "description": "여행 완료 보상",
      "created_at": "2024-01-01T08:45:00Z",
      "trip": 1
    }
  ]
}
```

### 📈 지갑 요약 정보
**GET** `/api/wallet/summary/`

**응답:**
```json
{
  "current_balance": 1500,
  "currency_code": "LCL",
  "total_earned": 2000,
  "total_spent": 500,
  "transaction_count": 25,
  "recent_transactions": [
    {
      "id": 1,
      "type": "earn",
      "amount": 100,
      "description": "여행 완료 보상",
      "created_at": "2024-01-01T08:45:00Z"
    }
  ]
}
```

---

## 🏪 제휴 상점 (Merchants)

### 📋 상점 목록 조회
**GET** `/api/merchants/list/?page=1&page_size=20&region=서울&category=음식점&search=카페`

**쿼리 파라미터:**
- `page` - 페이지 번호
- `page_size` - 페이지 크기 (최대 100)
- `region` - 지역 필터
- `category` - 카테고리 필터
- `search` - 상점명 검색

**응답:**
```json
{
  "merchants": [
    {
      "id": "1",
      "name": "스타벅스 강남점",
      "category": "음식점",
      "subcategory": "카페",
      "address": "서울시 강남구 테헤란로 123",
      "region": "서울 강남구",
      "lat": 37.5665,
      "lng": 126.9780,
      "phone": "02-1234-5678",
      "hours": {
        "weekday": "07:00-22:00",
        "weekend": "08:00-21:00"
      },
      "amenities": {
        "parking": "가능",
        "valet": "불가능",
        "pet_friendly": "가능",
        "vegetarian": "가능",
        "wheelchair": "가능"
      }
    }
  ],
  "pagination": {
    "count": 150,
    "next": "http://api.example.com/api/merchants/list/?page=2&page_size=20",
    "previous": null,
    "page": 1,
    "page_size": 20
  }
}
```

### 🗺️ 지도용 상점 마커
**GET** `/api/merchants/map/?region=서울&category=음식점&limit=50`

**응답:**
```json
{
  "markers": [
    {
      "id": "1",
      "name": "스타벅스 강남점",
      "lat": 37.5665,
      "lng": 126.9780,
      "category": "음식점",
      "address": "서울시 강남구 테헤란로 123"
    }
  ],
  "total_count": 150,
  "limit_applied": 50
}
```

### 🔍 상점 필터 옵션
**GET** `/api/merchants/filters/`

**응답:**
```json
{
  "regions": ["서울", "부산", "대구", "인천"],
  "categories": ["음식점", "카페", "편의점", "약국"],
  "total_merchants": 150
}
```

### 📖 상점 상세 정보
**GET** `/api/merchants/<merchant_id>/`

**응답:**
```json
{
  "id": "1",
  "name": "스타벅스 강남점",
  "category": "음식점",
  "subcategory": "카페",
  "address": "서울시 강남구 테헤란로 123",
  "region": "서울 강남구",
  "lat": 37.5665,
  "lng": 126.9780,
  "phone": "02-1234-5678",
  "hours": {
    "weekday": "07:00-22:00",
    "weekend": "08:00-21:00"
  },
  "amenities": {
    "parking": "가능",
    "valet": "불가능",
    "pet_friendly": "가능",
    "vegetarian": "가능",
    "wheelchair": "가능"
  }
}
```

---

## 📱 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 201 | Created | 리소스 생성 성공 |
| 400 | Bad Request | 잘못된 요청 |
| 401 | Unauthorized | 인증 필요 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스 없음 |
| 500 | Internal Server Error | 서버 오류 |

---

## 🔐 인증 헤더

JWT 토큰을 사용하는 API의 경우 다음 헤더를 포함해야 합니다:

```
Authorization: Bearer <access_token>
```

---

## 📝 에러 응답 형식

```json
{
  "error": "에러 메시지",
  "detail": "상세 에러 정보",
  "code": "ERROR_CODE"
}
```
