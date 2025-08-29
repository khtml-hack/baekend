from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """기본 사용자 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'nickname', 'address', 'address_lat', 'address_lng', 'zone_code', 'zone_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    address = serializers.CharField(required=False, allow_blank=True)
    address_lat = serializers.FloatField(required=False)
    address_lng = serializers.FloatField(required=False)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'address', 'address_lat', 'address_lng']
    
    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            # Django의 구체적인 에러 메시지를 한국어로 변환
            error_messages = []
            for error in e.error_list:
                if 'UserAttributeSimilarityValidator' in str(error):
                    error_messages.append("사용자 정보와 유사한 비밀번호는 사용할 수 없습니다.")
                elif 'MinimumLengthValidator' in str(error):
                    error_messages.append("비밀번호는 최소 8자 이상이어야 합니다.")
                elif 'CommonPasswordValidator' in str(error):
                    error_messages.append("너무 흔한 비밀번호입니다. 다른 비밀번호를 사용해주세요.")
                elif 'NumericPasswordValidator' in str(error):
                    error_messages.append("숫자만으로 구성된 비밀번호는 사용할 수 없습니다.")
                else:
                    error_messages.append(str(error))
            
            raise serializers.ValidationError(error_messages)
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        # 존 추론
        from .services.zone_service import infer_zone
        address = validated_data.get('address')
        lat = validated_data.get('address_lat')
        lng = validated_data.get('address_lng')
        zone = infer_zone(address=address, lat=lat, lng=lng)
        if zone:
            validated_data['zone_code'] = zone.get('code')
            validated_data['zone_name'] = zone.get('name')
        user = User.objects.create_user(**validated_data)
        return user


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'nickname', 'address', 'address_lat', 'address_lng', 'zone_code', 'zone_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def update(self, instance, validated_data):
        # 업데이트 가능한 필드 반영
        for field_name in ['nickname', 'address', 'address_lat', 'address_lng']:
            if field_name in validated_data:
                setattr(instance, field_name, validated_data[field_name])

        # 주소/좌표 변경 시 존 재계산
        if any(k in validated_data for k in ['address', 'address_lat', 'address_lng']):
            try:
                from .services.zone_service import infer_zone
                zone = infer_zone(
                    address=getattr(instance, 'address', None),
                    lat=getattr(instance, 'address_lat', None),
                    lng=getattr(instance, 'address_lng', None),
                )
                if zone:
                    instance.zone_code = zone.get('code')
                    instance.zone_name = zone.get('name')
            except Exception:
                pass

        instance.save()
        return instance


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


# ====== API 문서화를 위한 요청/응답 스키마 ======
class TokenObtainPairRequestSerializer(serializers.Serializer):
    """JWT 발급 요청 스키마 (email/password)"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenObtainPairResponseSerializer(serializers.Serializer):
    """JWT 발급 응답 스키마"""
    refresh = serializers.CharField()
    access = serializers.CharField()
    nickname_required = serializers.BooleanField()


class RegistrationResponseSerializer(serializers.Serializer):
    """회원가입 성공 응답 스키마"""
    user = MeSerializer()
    refresh = serializers.CharField()
    access = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    """로그아웃 요청 스키마 (리프레시 블랙리스트)"""
    refresh = serializers.CharField()