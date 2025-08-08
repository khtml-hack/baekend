from rest_framework import serializers
from .models import Recommendation, Trip, TripStatusLog


class RecommendationRequestSerializer(serializers.Serializer):
    origin_address = serializers.CharField(max_length=255)
    destination_address = serializers.CharField(max_length=255)
    region_code = serializers.CharField(max_length=20, required=False, allow_blank=True)


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = [
            'id', 'origin_address', 'destination_address', 
            'recommended_bucket', 'window_start', 'window_end',
            'expected_duration_min', 'expected_congestion_level',
            'rationale', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TripSerializer(serializers.ModelSerializer):
    recommendation = RecommendationSerializer(read_only=True)
    
    class Meta:
        model = Trip
        fields = [
            'id', 'recommendation', 'status', 'planned_departure',
            'started_at', 'arrived_at', 'predicted_duration_min',
            'actual_duration_min', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TripStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripStatusLog
        fields = ['id', 'status', 'logged_at']
        read_only_fields = ['id', 'logged_at']
