from rest_framework import serializers
from datetime import datetime, timedelta, timezone as dt_timezone
from .models import Recommendation, Trip, TripStatusLog


class RecommendationRequestSerializer(serializers.Serializer):
    origin_address = serializers.CharField(max_length=255)
    destination_address = serializers.CharField(max_length=255)
    region_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    # 선택: 도착 마감 시각과 탐색 범위(분)
    arrive_by = serializers.CharField(required=False, help_text="도착 마감 시각 HH:MM 또는 ISO8601(예: 2025-08-29T12:25:00.000Z)")
    window_minutes = serializers.IntegerField(required=False, min_value=10, max_value=360, help_text="arrive_by 기준 역탐색 범위(분), 기본 120")

    def validate_arrive_by(self, value):
        """arrive_by를 'HH:MM' 또는 ISO8601(datetime)로 받아 'HH:MM'로 정규화."""
        if value in (None, ""):
            return value

        text = str(value).strip()

        # 1) HH:MM 형식 허용
        try:
            datetime.strptime(text, "%H:%M")
            return text
        except ValueError:
            pass

        # 2) ISO8601 형식 허용 (Z를 +00:00으로 치환하여 파싱)
        try:
            iso_text = text.replace("Z", "+00:00")
            dt_obj = datetime.fromisoformat(iso_text)
            if dt_obj.tzinfo is None:
                # 타임존이 없으면 UTC로 가정
                dt_obj = dt_obj.replace(tzinfo=dt_timezone.utc)
            # KST(Asia/Seoul, UTC+9)로 변환 후 HH:MM 반환
            kst = dt_obj.astimezone(dt_timezone(timedelta(hours=9)))
            return kst.strftime("%H:%M")
        except Exception:
            raise serializers.ValidationError("arrive_by는 'HH:MM' 또는 ISO8601(datetime) 형식이어야 합니다.")


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
class SearchWindowSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class UIOptionSerializer(serializers.Serializer):
    title = serializers.CharField()
    depart_in_text = serializers.CharField()
    window = SearchWindowSerializer()
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


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class RecommendationCreateResponseSerializer(serializers.Serializer):
    recommendation_id = serializers.IntegerField()
    ui = UIBlockSerializer()
    origin_address = serializers.CharField()
    destination_address = serializers.CharField()
    origin_location = LocationSerializer()
    destination_location = LocationSerializer()
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


    


class OptimalTravelTimeResponseSerializer(serializers.Serializer):
    optimal_time = OptimalTimeSerializer()
    alternative_times = OptimalTimeSerializer(many=True)
    search_window = SearchWindowSerializer()
    location = serializers.CharField()
    precision = serializers.CharField()
    analyzed_minutes = serializers.IntegerField()

    