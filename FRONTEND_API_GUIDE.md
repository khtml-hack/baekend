# 🚀 API Quick Reference

## 🔗 주요 엔드포인트 요약

### 🔐 인증
```javascript
// 회원가입
POST /api/users/register/
{
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123",
  "username": "username",
  "nickname": "닉네임"
}

// 로그인
POST /api/users/login/
{
  "email": "user@example.com", 
  "password": "password123"
}
// → Returns: { "access": "jwt_token", "refresh": "refresh_token" }
```

### 🎯 AI 추천 & 여행
```javascript
// 1. AI 추천 받기
POST /api/trips/recommend/
{
  "origin_address": "서울역",
  "destination_address": "강남역"
}
// → Returns: recommendation_id, 추천 시간대, 예상 보상

// 2. 출발 보상 미리보기
GET /api/rewards/preview/{trip_id}/
// → Returns: 예상 보상 금액, 보너스 정보

// 3. 여행 시작 (보상 즉시 지급!)
POST /api/trips/start/{recommendation_id}/
// → Returns: trip_id + 출발 보상 결과

// 4. 여행 완료 (추가 보상 지급!)
POST /api/trips/arrive/{trip_id}/
// → Returns: 완료 보상 결과
```

### 💰 보상 조회
```javascript
// 지갑 정보
GET /api/rewards/
// → Returns: 잔액, 최근 거래내역

// 보상 요약
GET /api/rewards/summary/
// → Returns: 총 적립/사용, 거래 건수

// 거래 내역
GET /api/rewards/transactions/
// → Returns: 페이징된 거래 내역
```

## 🎮 보상 시스템 핵심

### 💰 보상 금액 계산
```
출발 보상 = 100원 × (1 + 보너스들)

보너스:
✅ AI 추천 시간 출발: +30%
✅ 혼잡도 낮음: +50%
✅ 새벽시간(T6): +40%
✅ 밤시간(T5): +30%
✅ 오전/오후(T1,T3): +20%

최대: 240원 (2.4배)
```

### ⏰ 시간대 구분
```
T0: 06:00-09:00 (아침)    +10%
T1: 09:00-12:00 (오전)    +20%
T2: 12:00-15:00 (점심)    +10%
T3: 15:00-18:00 (오후)    +20%
T4: 18:00-21:00 (저녁)    +10%
T5: 21:00-00:00 (밤)      +30%
T6: 00:00-06:00 (새벽)    +40%
```

## �️ 지도 구현 가이드

### 1. 지도에 제휴 상점 표시
```javascript
// 사용자 위치 기반 상점 조회
const fetchMerchants = async (lat, lng, radius = 5) => {
  const response = await fetch(
    `/api/merchants/map/?lat=${lat}&lng=${lng}&radius=${radius}`
  );
  const data = await response.json();
  return data.merchants;
};

// 지도 마커 생성
const createMarkers = (merchants) => {
  return merchants.map(merchant => ({
    id: merchant.id,
    position: { lat: merchant.lat, lng: merchant.lng },
    title: merchant.name,
    category: merchant.category,
    distance: merchant.distance,
    // 카테고리별 아이콘 색상
    icon: getCategoryIcon(merchant.category)
  }));
};

// 카테고리별 아이콘 설정
const getCategoryIcon = (category) => {
  const iconColors = {
    '카페': '#8B4513',     // 갈색
    '한식': '#FF6B35',     // 주황색
    '중식': '#FF0000',     // 빨간색
    '일식': '#4169E1',     // 파란색
    '패스트푸드': '#FFD700' // 노란색
  };
  return iconColors[category] || '#808080';
};
```

### 2. 실시간 필터링
```javascript
const [merchants, setMerchants] = useState([]);
const [selectedCategory, setSelectedCategory] = useState('');
const [searchRadius, setSearchRadius] = useState(5);

// 카테고리 변경 시 재조회
useEffect(() => {
  if (userLocation) {
    fetchMerchantsWithFilter(
      userLocation.lat, 
      userLocation.lng, 
      searchRadius,
      selectedCategory
    );
  }
}, [selectedCategory, searchRadius, userLocation]);

const fetchMerchantsWithFilter = async (lat, lng, radius, category) => {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lng: lng.toString(), 
    radius: radius.toString()
  });
  
  if (category) params.append('category', category);
  
  const response = await fetch(`/api/merchants/map/?${params}`);
  const data = await response.json();
  setMerchants(data.merchants);
};
```

### 3. 상점 정보 팝업
```javascript
const MerchantInfoWindow = ({ merchant }) => (
  <div className="merchant-popup">
    <h3>{merchant.name}</h3>
    <p className="category">{merchant.category}</p>
    <p className="distance">{merchant.distance}km</p>
    <p className="address">{merchant.address}</p>
    
    {/* 운영 시간 */}
    <div className="hours">
      <p>평일: {merchant.hours.weekday}</p>
      <p>주말: {merchant.hours.weekend}</p>
    </div>
    
    {/* 편의 시설 */}
    <div className="features">
      {merchant.features.parking && <span className="feature">🅿️ 주차</span>}
      {merchant.features.pet_friendly && <span className="feature">🐕 반려동물</span>}
      {merchant.features.vegetarian && <span className="feature">🥗 채식</span>}
      {merchant.features.wheelchair && <span className="feature">♿ 휠체어</span>}
    </div>
    
    {/* 전화번호 */}
    {merchant.phone !== '정보없음' && (
      <a href={`tel:${merchant.phone}`} className="phone">
        📞 {merchant.phone}
      </a>
    )}
  </div>
);
```

### 4. 성능 최적화
```javascript
// 지도 이동 시 디바운스 적용
const debouncedSearch = useCallback(
  debounce((lat, lng) => {
    fetchMerchantsWithFilter(lat, lng, searchRadius, selectedCategory);
  }, 500),
  [searchRadius, selectedCategory]
);

// 지도 범위 변경 이벤트
const handleMapBoundsChanged = (map) => {
  const center = map.getCenter();
  debouncedSearch(center.lat(), center.lng());
};

// 마커 클러스터링 (많은 상점이 있을 때)
const MarkerClusterer = ({ merchants, map }) => {
  useEffect(() => {
    if (!map || !merchants.length) return;
    
    const clusterer = new window.MarkerClusterer(map, markers, {
      imagePath: 'https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/m',
      maxZoom: 15
    });
    
    return () => clusterer.clearMarkers();
  }, [merchants, map]);
};
```

### 1. JWT 토큰 관리
```javascript
// localStorage에 토큰 저장
localStorage.setItem('access_token', response.access);
localStorage.setItem('refresh_token', response.refresh);

// API 요청 시 헤더 추가
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json'
};
```

### 2. 보상 표시 UI 패턴
```javascript
// 출발 전 보상 미리보기
const previewReward = await fetch(`/api/rewards/preview/${tripId}/`);
// → "예상 보상: 180원 (1.8x 보너스!)" 

// 출발 시 보상 애니메이션
const startResult = await fetch(`/api/trips/start/${recommendationId}/`);
if (startResult.departure_reward.success) {
  showRewardAnimation(startResult.departure_reward.reward_info.amount);
}
```

### 3. 상태 관리 예시
```javascript
const [userState, setUserState] = useState({
  isLoggedIn: false,
  balance: 0,
  currentTrip: null,
  pendingReward: 0
});

// 여행 시작 시
const startTrip = async (recommendationId) => {
  const result = await api.post(`/trips/start/${recommendationId}/`);
  setUserState(prev => ({
    ...prev,
    currentTrip: result.trip_id,
    balance: prev.balance + result.departure_reward.reward_info.amount
  }));
};
```

### 4. 에러 처리
```javascript
const apiCall = async (url, options) => {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.status === 401) {
      // 토큰 만료 → 로그인 페이지로 리다이렉트
      redirectToLogin();
      return;
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    showErrorMessage('네트워크 오류가 발생했습니다.');
  }
};
```

## 🎨 UI/UX 권장사항

### 보상 표시
- 💰 출발 전: "예상 보상 150원!" (미리보기)
- ✨ 출발 시: 애니메이션으로 "150원 적립!" 
- 🎉 완료 시: "추가 보상 80원!"

### 시간 추천 표시
```
🟢 매우 좋음 (1.0-2.0): 초록색
🔵 좋음 (2.0-2.5): 파란색  
🟡 보통 (2.5-3.5): 노란색
🟠 혼잡 (3.5-4.0): 주황색
🔴 매우 혼잡 (4.0+): 빨간색
```

### 보상 히스토리
```
📈 총 적립: 2,000원
📉 총 사용: 500원
💳 현재 잔액: 1,500원
🏆 이번 달 보상: 800원
```

## 🚀 개발 우선순위

### Phase 1 (필수)
1. 사용자 인증 (로그인/회원가입)
2. AI 추천 받기
3. 출발/도착 처리
4. 기본 보상 표시

### Phase 2 (개선)
1. 보상 미리보기
2. 최적 시간 추천
3. 보상 히스토리
4. 애니메이션 효과

### Phase 3 (고도화)  
1. 프로필 관리
2. 제휴 상점 연동
3. 보상 사용 기능
4. 통계 대시보드

---

**💡 Tip**: `/api/docs/` 에서 실시간으로 API 테스트 가능!
