from rest_framework import serializers
from .models import UserConsent, UserRoute


class UserConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConsent
        fields = ['id', 'consent_type', 'consent_status', 'consented_at']
        read_only_fields = ['id', 'consented_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRoute
        fields = ['id', 'route_type', 'address', 'lat', 'lng', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_route_type(self, value):
        # 허용된 표준값으로 정규화 (동의어/영문 허용)
        raw = str(value).strip()
        mapping = {
            '집': '집', 'home': '집', '자택': '집',
            '직장': '직장', '회사': '직장', 'work': '직장', 'office': '직장',
            '학교': '학교', 'school': '학교'
        }
        normalized = mapping.get(raw.lower() if raw.isascii() else raw, raw)
        if normalized not in ['집', '직장', '학교']:
            raise serializers.ValidationError("유효하지 않은 경로 타입입니다. (허용: 집/직장/학교)")
        return normalized

    def validate_lat(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("위도는 -90에서 90 사이의 값이어야 합니다.")
        return value

    def validate_lng(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("경도는 -180에서 180 사이의 값이어야 합니다.")
        return value
