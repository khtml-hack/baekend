from rest_framework.views import APIView
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiResponse
)
from .serializers import (
    UserRegistrationSerializer,
    MeSerializer,
    NicknameSerializer,
    CustomTokenObtainPairSerializer,
    RegistrationResponseSerializer,
    TokenObtainPairRequestSerializer,
    TokenObtainPairResponseSerializer,
    LogoutRequestSerializer,
)

User = get_user_model()


@extend_schema_view(
    post=extend_schema(
        tags=["Users"],
        summary="회원가입",
        request=UserRegistrationSerializer,
        responses={
            201: RegistrationResponseSerializer,
            400: OpenApiResponse(description="입력값 검증 실패"),
        },
    )
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': MeSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=["Users"],
        summary="내 프로필 조회",
        responses={200: MeSerializer},
    ),
    patch=extend_schema(
        tags=["Users"],
        summary="내 프로필 수정",
        request=MeSerializer,
        responses={200: MeSerializer},
    ),
)
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


@extend_schema_view(
    patch=extend_schema(
        tags=["Users"],
        summary="닉네임 설정/변경",
        request=NicknameSerializer,
        responses={200: NicknameSerializer},
    )
)
class NicknameView(generics.UpdateAPIView):
    serializer_class = NicknameSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


@extend_schema_view(
    post=extend_schema(
        tags=["Users"],
        summary="로그인 (JWT 발급)",
        request=TokenObtainPairRequestSerializer,
        responses={200: TokenObtainPairResponseSerializer},
    )
)
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["Users"],
        summary="로그아웃 (리프레시 블랙리스트)",
        request=LogoutRequestSerializer,
        responses={205: OpenApiResponse(description="로그아웃 완료"), 400: OpenApiResponse(description="요청 오류")},
    )
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'refresh 토큰이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
