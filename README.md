## Baekend API (Django + DRF)

AI 기반 여행 추천 및 제휴 상점 서비스의 백엔드 API입니다. Django REST Framework, JWT 인증, drf-spectacular 기반 문서화를 사용합니다. 운영은 Gunicorn(+Nginx), Docker, Cloudtype 배포를 지원합니다.

### 주요 스택
- **Framework**: Django 4.2, Django REST Framework
- **Auth**: JWT (simplejwt)
- **Docs**: drf-spectacular (OpenAPI/Swagger/Redoc)
- **DB**: MySQL (프로덕션 기본), 로컬은 SQLite 대체 가능
- **Server/Static**: Gunicorn, WhiteNoise
- **Infra**: Docker, docker-compose, Nginx, Cloudtype

### 모듈(앱)
- **users**: 커스텀 사용자 모델 및 인증
- **profiles**: 사용자 프로필/경로 등
- **trips**: 여행 관련 기능
- **rewards (wallet)**: 리워드/지갑
- **merchants**: 제휴 상점
- **integrations**, **common**: 통합/공통 유틸

### API 문서 경로
- **Swagger UI**: `/api/docs/`
- **Redoc**: `/api/redoc/`
- **Schema (OpenAPI)**: `/api/schema/`

---

## 빠른 시작 (로컬 개발)

### 1) 사전 준비
- Python 3.10.x
- (선택) MySQL 8.x — 로컬에서 MySQL 없이 시작하려면 아래의 `local_settings.py`로 SQLite 사용 권장

### 2) 의존성 설치
```bash
python -m venv .venv
. .venv/bin/activate         # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) 환경 변수 파일 생성 (`.env`)
아래 예시를 참고해 루트에 `.env` 파일을 만듭니다.
```env
# 필수
SECRET_KEY=change-me

# 프로덕션/배포 감지용 (선택)
ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1

# DB (MySQL 사용 시)
DB_NAME=your_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
# DB_PORT는 settings에서 3306 고정

# 외부 API 키 (선택)
OPENAI_API_KEY=
KAKAO_API_KEY=
TMAP_APP_KEY=
```

### 4) 로컬은 SQLite로 간단 시작 (권장)
`config/local_settings.py` 파일을 만들면 기본 설정을 덮어쓸 수 있습니다. 아래 내용으로 빠르게 실행해보세요.
```python
# config/local_settings.py
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

### 5) 마이그레이션/실행
```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

브라우저에서 `http://127.0.0.1:8000/api/docs/`로 접속해 API 문서를 확인합니다.

### 6) 관리자 계정(선택)
```bash
python manage.py createsuperuser
```

---

## MySQL로 실행 (로컬/프로덕션)
`config/settings.py`는 기본적으로 MySQL을 사용하도록 구성되어 있습니다. 아래 환경 변수가 필요합니다.
- **DB_NAME**, **DB_USER**, **DB_PASSWORD**, **DB_HOST** (포트는 3306 고정)

로컬에서 MySQL을 사용하려면 MySQL 실행 후 `.env`를 올바르게 채우고 마이그레이션을 진행하세요.

---

## Docker로 실행

### 1) 빌드 및 실행
```bash
docker compose up -d --build
```

- 백엔드: `http://localhost:8000`
- Nginx(프록시): `http://localhost` (80), `https://localhost` (443)
- 정적/미디어는 `./static`, `./media` 볼륨에 마운트됩니다.

### 2) 초기화
컨테이너 안에서 마이그레이션/슈퍼유저를 생성할 수 있습니다.
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

---

## Cloudtype 배포
`cloudtype.yaml`에 따라 다음이 자동으로 실행됩니다.
- `pip install -r requirements.txt`
- `python manage.py collectstatic --noinput`
- `python manage.py migrate --noinput`
- `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2`

배포 시 필수 환경 변수:
- **SECRET_KEY**
- **DB_NAME**, **DB_USER**, **DB_PASSWORD**, **DB_HOST** (MySQL)
- (선택) **ALLOWED_HOSTS**, **CLOUDTYPE_HOST**, **OPENAI_API_KEY**, **KAKAO_API_KEY**, **TMAP_APP_KEY**

배포 후 API 문서: `https://<배포도메인>/api/docs/`

---

## 유용한 명령어
- **마이그레이션 생성/적용**
  - `python manage.py makemigrations`
  - `python manage.py migrate`
- **정적 파일 수집(배포용)**
  - `python manage.py collectstatic --noinput`
- **관리자 계정 생성**
  - `python manage.py createsuperuser`

---

## 트러블슈팅
- **SECRET_KEY 오류**: `.env`에 `SECRET_KEY`를 반드시 설정하세요.
- **CORS/CSRF 문제**: 개발 중에는 `CORS_ALLOW_ALL_ORIGINS=True`로 허용. 배포 시 `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`를 환경에 맞게 설정하세요.
- **DB 연결 실패**: MySQL 환경 변수 확인. 로컬은 `config/local_settings.py`로 SQLite 사용을 권장합니다.

---

## 라이선스
사내/프로젝트 정책에 따릅니다. 필요 시 라이선스를 추가하세요.


