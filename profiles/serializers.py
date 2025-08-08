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
        if value not in ['집', '직장', '학교']:
            raise serializers.ValidationError("유효하지 않은 경로 타입입니다.")
        return value

    def validate_lat(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError("위도는 -90에서 90 사이의 값이어야 합니다.")
        return value

    def validate_lng(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError("경도는 -180에서 180 사이의 값이어야 합니다.")
        return value
