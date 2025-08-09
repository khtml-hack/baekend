from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, MeSerializer, NicknameSerializer

User = get_user_model()


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
            'nickname_required': user.nickname is None or user.nickname == '',
        }, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class NicknameView(generics.UpdateAPIView):
    serializer_class = NicknameSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
