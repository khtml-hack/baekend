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


# ====== API 문서화를 위한 요청/응답 스키마 ======
class UIOptionSerializer(serializers.Serializer):
    title = serializers.CharField()
    depart_in_text = serializers.CharField()
    window = serializers.DictField()
    optimal_departure_time = serializers.CharField()
    expected_duration_min = serializers.IntegerField()
    congestion_level = serializers.FloatField()
    congestion_description = serializers.CharField()
    time_saved_min = serializers.IntegerField()
    reward_amount = serializers.IntegerField()


class UICurrentSerializer(serializers.Serializer):
    departure_time = serializers.CharField()
    arrival_time = serializers.CharField()
    duration_min = serializers.IntegerField()
    congestion_level = serializers.FloatField()
    congestion_description = serializers.CharField()


class UIBlockSerializer(serializers.Serializer):
    current = UICurrentSerializer()
    options = UIOptionSerializer(many=True)
    tmap_summary = serializers.DictField(required=False)
    tmap_meta = serializers.DictField(required=False)


class RecommendationCreateResponseSerializer(serializers.Serializer):
    recommendation_id = serializers.IntegerField()
    ui = UIBlockSerializer()
    origin_address = serializers.CharField()
    destination_address = serializers.CharField()
    ai_confidence = serializers.CharField()


class TripStartResponseSerializer(TripSerializer):
    message = serializers.CharField()
    class Meta(TripSerializer.Meta):
        fields = TripSerializer.Meta.fields + ['message']


class TripArriveResponseSerializer(TripSerializer):
    completion_reward = serializers.JSONField()
    class Meta(TripSerializer.Meta):
        fields = TripSerializer.Meta.fields + ['completion_reward']


class OptimalTimeSerializer(serializers.Serializer):
    time = serializers.CharField()
    congestion_score = serializers.FloatField()


class SearchWindowSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class OptimalTravelTimeResponseSerializer(serializers.Serializer):
    optimal_time = OptimalTimeSerializer()
    alternative_times = OptimalTimeSerializer(many=True)
    search_window = SearchWindowSerializer()
    location = serializers.CharField()
    precision = serializers.CharField()
    analyzed_minutes = serializers.IntegerField()