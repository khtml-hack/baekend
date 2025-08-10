from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

# .env 파일 로드
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------------------
# 기본 환경 설정
# ----------------------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# 쉼표 구분 문자열을 리스트로 변환
def csv(name, default=""):
    return [s.strip() for s in os.getenv(name, default).split(",") if s.strip()]

# Proxy 환경에서 Host/Proto 신뢰 (Cloudtype 대응)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ----------------------------
# Host / CSRF / CORS
# ----------------------------
ALLOWED_HOSTS = csv("ALLOWED_HOSTS", ".cloudtype.app,localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = csv("CSRF_TRUSTED_ORIGINS", "https://*.cloudtype.app")
CORS_ALLOWED_ORIGINS = csv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,https://localhost:3000")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ----------------------------
# 앱 설정
# ----------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'corsheaders',
    'users',
    'profiles',
    'trips',
    'rewards',
    'merchants',
    'common',
    'integrations',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ----------------------------
# DB (현재 SQLite, 필요시 MySQL로 변경)
# ----------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ----------------------------
# 비밀번호 정책
# ----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# ----------------------------
# 언어 / 시간대
# ----------------------------
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = False

# ----------------------------
# 정적 파일
# ----------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

# ----------------------------
# REST Framework / JWT
# ----------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Backend API',
    'DESCRIPTION': 'AI 기반 여행 추천 및 제휴 상점 서비스 API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ----------------------------
# API 키
# ----------------------------
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables")

KAKAO_API_KEY = os.getenv('KAKAO_API_KEY')
if not KAKAO_API_KEY:
    print("Warning: KAKAO_API_KEY not found in environment variables")

# ----------------------------
# 혼잡도 버킷
# ----------------------------
CONGESTION_BUCKETS = {
    'T0': {'start': '06:00', 'end': '09:00', 'name': '오전 시간대'},
    'T1': {'start': '09:00', 'end': '12:00', 'name': '오전 늦은 시간'},
    'T2': {'start': '12:00', 'end': '15:00', 'name': '점심 시간대'},
    'T3': {'start': '15:00', 'end': '18:00', 'name': '오후 시간대'},
    'T4': {'start': '18:00', 'end': '21:00', 'name': '저녁 시간대'},
    'T5': {'start': '21:00', 'end': '24:00', 'name': '밤 시간대'},
    'T6': {'start': '00:00', 'end': '06:00', 'name': '새벽 시간대'},
}
