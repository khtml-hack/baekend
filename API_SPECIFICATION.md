# 🚀 AI 기반 교통 혼잡도 여행 추천 서비스 API 명세서

## 📋 기본 정보
- **Base URL**: `http://your-domain.com/api`
- **인증 방식**: JWT Bearer Token
- **응답 형식**: JSON
- **API 문서**: `http://your-domain.com/api/docs/` (Swagger UI)

---

## 🔐 인증 (Authentication)

### 1. 사용자 회원가입
```http
POST /api/users/register/
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "username": "username"
}
```

**Response (201):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "nickname": null,
    "date_joined": "2025-08-09T10:30:00Z"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "nickname_required": true
}
```

설명:
- 회원가입 시 닉네임은 받지 않습니다. 가입 직후 발급된 토큰으로 닉네임 설정 API를 즉시 호출합니다.

### 2. 로그인 (JWT 토큰 발급)
```http
POST /api/users/login/
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 3. 토큰 갱신
```http
POST /api/users/token/refresh/
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

## 👤 사용자 관리 (Users)

### 1. 내 정보 조회/수정
```http
GET/PUT /api/users/me/
Authorization: Bearer {access_token}
```

**Response (GET):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username", 
  "nickname": "닉네임",
  "date_joined": "2025-08-09T10:30:00Z"
}
```

### 2. 닉네임 수정 (회원가입 직후 권장)
```http
PUT /api/users/nickname/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "nickname": "새로운닉네임"
}
```

설명:
- 회원가입 응답의 `nickname_required`가 `true`이면 즉시 이 엔드포인트를 호출하여 닉네임을 설정합니다.

---

## 🎯 여행 추천 (Trips)

### 1. AI 추천 생성
```http
POST /api/trips/recommend/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "origin_address": "서울역",
  "destination_address": "강남역",
  "region_code": "seoul" // 선택사항
}
```

**Response (201):**
```json
{
  "recommendation_id": 1,
  "recommended_bucket": "T1",
  "recommended_window": {
    "start": "09:00",
    "end": "10:00"
  },
  "rationale": "오전 시간대가 가장 적합합니다. 혼잡도가 낮아 빠른 이동이 가능합니다.",
  "expected_duration_min": 45,
  "expected_congestion_level": "좋음",
  "origin_address": "서울특별시 중구 세종대로 2 서울역",
  "destination_address": "서울특별시 강남구 강남대로 396 강남역"
}
```

### 2. 여행 시작 (+ 출발 보상 지급)
```http
POST /api/trips/start/{recommendation_id}/
Authorization: Bearer {access_token}
```

**Response (201):**
```json
{
  "trip_id": 1,
  "status": "ongoing",
  "started_at": "2025-08-09T09:15:00Z",
  "planned_departure": "2025-08-09T09:00:00Z",
  "predicted_duration_min": 45,
  "recommendation": {
    "id": 1,
    "origin_address": "서울역",
    "destination_address": "강남역",
    "recommended_bucket": "T1"
  },
  "departure_reward": {
    "success": true,
    "transaction_id": 123,
    "reward_info": {
      "amount": 150,
      "base_reward": 100,
      "multiplier": 1.5,
      "bonus_type": "time_window",
      "bucket_bonus": 0.2
    },
    "message": "출발 보상 150원이 적립되었습니다! (배율: 1.5x)"
  }
}
```

### 3. 여행 완료 (+ 완료 보상 지급)
```http
POST /api/trips/arrive/{trip_id}/
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "trip_id": 1,
  "status": "arrived",
  "arrived_at": "2025-08-09T10:00:00Z",
  "actual_duration_min": 42,
  "completion_reward": {
    "success": true,
    "transaction_id": 124,
    "amount": 80,
    "description": "여행 완료 보상 (시간 예측 정확도 보너스 +30원)"
  }
}
```

### 4. 여행 내역 조회
```http
GET /api/trips/history/
Authorization: Bearer {access_token}
```

### 5. 최적 시간 조회
```http
GET /api/trips/optimal-time/?window_hours=2&location=gangnam
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "optimal_window": {
    "slot_start": "2025-08-09 14:30:00",
    "slot_end": "2025-08-09 15:00:00",
    "congestion_score": 1.8,
    "bucket_code": "T3",
    "bucket_name": "오후 시간대",
    "recommendation_level": "좋음"
  },
  "alternatives": [
    {
      "slot_start": "2025-08-09 15:00:00",
      "slot_end": "2025-08-09 15:30:00",
      "congestion_score": 2.1,
      "recommendation_level": "좋음"
    }
  ],
  "recommendation_reason": "30분 후 출발하는 오후 시간대가 가장 적합합니다. 예상 혼잡도: 좋음"
}
```

---

## 💰 보상 시스템 (Rewards)

### 1. 지갑 정보 조회
```http
GET /api/rewards/
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "id": 1,
  "balance": 1500,
  "currency_code": "LCL",
  "created_at": "2025-08-09T10:30:00Z",
  "updated_at": "2025-08-09T15:45:00Z",
  "recent_transactions": [
    {
      "id": 123,
      "type": "earn",
      "amount": 150,
      "description": "AI 추천 시간대 출발 보너스 - 서울역 → 강남역",
      "created_at": "2025-08-09T09:15:00Z",
      "trip": 1
    }
  ]
}
```

### 2. 출발 보상 미리보기
```http
GET /api/rewards/preview/{trip_id}/
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "trip_id": 1,
  "expected_reward": 180,
  "base_reward": 100,
  "multiplier": 1.8,
  "bonus_type": "low_congestion",
  "bonus_description": "혼잡도 낮은 시간대 출발 보너스",
  "bucket_bonus": 0.3,
  "recommendation_info": {
    "bucket": "T6",
    "window_start": "02:00",
    "window_end": "06:00",
    "congestion_level": 1
  }
}
```

### 3. 보상 요약 정보
```http
GET /api/rewards/summary/
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "current_balance": 1500,
  "currency_code": "LCL",
  "total_earned": 2000,
  "total_spent": 500,
  "transaction_count": 15,
  "recent_transactions": [
    {
      "id": 124,
      "type": "earn",
      "amount": 80,
      "description": "여행 완료 보상",
      "created_at": "2025-08-09T10:00:00Z"
    }
  ]
}
```

### 4. 거래 내역 조회
```http
GET /api/rewards/transactions/?page=1&page_size=20
Authorization: Bearer {access_token}
```

---

## 👥 프로필 (Profiles)

### 1. 동의 정보 생성
```http
POST /api/profiles/consents/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "consent_type": "marketing",
  "consent_status": true
}
```

### 2. 자주 가는 장소 등록
```http
POST /api/profiles/routes/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "route_type": "집",
  "address": "서울시 강남구 삼성동",
  "lat": 37.5665,
  "lng": 126.9780
}
```

### 3. 자주 가는 장소 조회
```http
GET /api/profiles/routes/
Authorization: Bearer {access_token}
```

---

## 🏪 제휴 상점 (Merchants)

### 1. 상점 목록 조회
```http
GET /api/merchants/list/?page=1&page_size=20&region=서울특별시&category=카페&search=스타벅스
```

**Query Parameters:**
- `page`: 페이지 번호 (기본값: 1)
- `page_size`: 페이지 크기 (기본값: 20, 최대: 100)
- `region`: 지역 필터 (예: "서울특별시", "부산광역시")
- `category`: 카테고리 필터 (예: "카페", "음식점")
- `search`: 상점명 검색

**Response (200):**
```json
{
  "merchants": [
    {
      "id": "1",
      "시설명": "스타벅스 강남점",
      "카테고리": "카페",
      "세부카테고리": "커피전문점",
      "소재지": "서울시 강남구 테헤란로 123",
      "지역": "서울특별시",
      "latitude": 37.5665,
      "longitude": 126.9780,
      "전화번호": "02-1234-5678",
      "운영시간": "07:00~22:00",
      "편의시설": {
        "주차장": "가능",
        "발렛파킹": "불가능",
        "반려동물동반": "가능",
        "채식메뉴": "보유",
        "장애인편의": "보유"
      }
    }
  ],
  "pagination": {
    "current_page": 1,
    "page_size": 20,
    "total_count": 2192,
    "total_pages": 110,
    "has_next": true,
    "has_previous": false
  }
}
```

### 2. 지도 마커 데이터
```http
GET /api/merchants/map/?region=서울특별시&category=카페&limit=100
```

**Query Parameters:**
- `region`: 지역 필터 (선택사항)
- `category`: 카테고리 필터 (선택사항)
- `limit`: 최대 개수 (기본값: 500, 최대: 2000)

**Response (200):**
```json
{
  "markers": [
    {
      "id": "1",
      "시설명": "스타벅스 강남점",
      "latitude": 37.5665,
      "longitude": 126.9780,
      "카테고리": "카페",
      "소재지": "서울시 강남구 테헤란로 123"
    }
  ],
  "total_count": 500,
  "limit_applied": true
}
```

### 3. 상점 상세 정보
```http
GET /api/merchants/{merchant_id}/
```

**Response (200):**
```json
{
  "merchant": {
    "id": "1",
    "시설명": "스타벅스 강남점",
    "카테고리": "카페",
    "세부카테고리": "커피전문점",
    "소재지": "서울시 강남구 테헤란로 123",
    "지역": "서울특별시",
    "latitude": 37.5665,
    "longitude": 126.9780,
    "전화번호": "02-1234-5678",
    "운영시간": "07:00~22:00",
    "편의시설": {
      "주차장": "가능",
      "발렛파킹": "불가능",
      "반려동물동반": "가능",
      "채식메뉴": "보유",
      "장애인편의": "보유"
    }
  }
}
```

### 4. 필터 옵션 목록
```http
GET /api/merchants/filters/
```

**Response (200):**
```json
{
  "regions": [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "경기도",
    "강원도",
    "충청북도",
    "충청남도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
    "세종특별자치시"
  ],
  "categories": [
    "카페",
    "음식점",
    "편의점",
    "마트",
    "병원",
    "약국",
    "주유소",
    "숙박",
    "문화시설",
    "교육시설",
    "공공시설",
    "기타"
  ],
  "total_merchants": 2192
}
```

---

## 🎮 보상 시스템 특징

### 💡 보상 계산 로직
```
출발 시 보상 = 기본 100원 × 보너스 배율

보너스 종류:
- AI 추천 시간대 출발: +30%
- 혼잡도 낮은 시간: +50% 
- 시간대별 보너스:
  * T6 (새벽 00:00-06:00): +40%
  * T5 (밤 21:00-00:00): +30%
  * T1, T3 (오전/오후): +20%
  * T0, T2, T4: +10%

완료 시 보상 = 기본 50원 + 정확도 보너스
- 예측 시간 ±5분 이내: +30원
- 예측 시간 ±10분 이내: +15원
```

### 🎯 시간대 분류 (Time Buckets)
- **T0**: 06:00-09:00 (아침 출근시간)
- **T1**: 09:00-12:00 (오전 시간) 
- **T2**: 12:00-15:00 (점심 시간)
- **T3**: 15:00-18:00 (오후 시간)
- **T4**: 18:00-21:00 (저녁 퇴근시간)
- **T5**: 21:00-00:00 (밤 시간)
- **T6**: 00:00-06:00 (새벽 시간)

---

## ⚠️ 에러 응답

### 인증 오류 (401)
```json
{
  "detail": "자격 증명이 제공되지 않았습니다."
}
```

### 권한 오류 (403)
```json
{
  "detail": "이 작업을 수행할 권한이 없습니다."
}
```

### 유효성 검증 오류 (400)
```json
{
  "field_name": ["이 필드는 필수입니다."]
}
```

### 서버 오류 (500)
```json
{
  "error": "내부 서버 오류가 발생했습니다."
}
```

---

## 🔄 API 사용 플로우

### 1. 기본 사용자 플로우
```
회원가입 → (토큰 수령) → 닉네임 설정 → 추천 요청 → 출발 → 보상 확인 → 도착 → 추가 보상
```

### 2. 보상 최적화 플로우
```
추천 요청 → 보상 미리보기 → 최적 시간 확인 → 전략적 출발 → 최대 보상 획득
```

### 3. 프로필 설정 플로우
```
로그인 → 자주 가는 장소 등록 → 동의 설정 → 개인화된 추천 받기
```

---

## 📝 개발 참고사항

### Headers
모든 인증이 필요한 요청에는 다음 헤더 포함:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Rate Limiting
- 일반 API: 분당 100회
- 추천 API: 분당 20회
- 로그인 API: 분당 10회

### 페이징
대부분의 목록 API는 페이징 지원:
```
?page=1&page_size=20
```

### API 문서
실시간 API 테스트: `http://your-domain.com/api/docs/`

---

**🎉 새로운 AI 기반 보상 시스템으로 사용자 참여도를 높이세요!**
