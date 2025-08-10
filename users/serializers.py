from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """기본 사용자 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'nickname', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'nickname', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class NicknameSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(max_length=50)

    class Meta:
        model = User
        fields = ['nickname']

    def validate_nickname(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(nickname=value).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """로그인 시 닉네임 필요 여부 플래그를 응답에 포함"""
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['nickname_required'] = not bool(user.nickname)
        return data
