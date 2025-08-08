from django.contrib import admin
from .models import CongestionIndex, Recommendation, Trip, TripStatusLog


@admin.register(CongestionIndex)
class CongestionIndexAdmin(admin.ModelAdmin):
    list_display = ['month', 'region_code', 'T0', 'T1', 'T2', 'T3', 'version', 'created_at']
    list_filter = ['version', 'month', 'region_code']
    search_fields = ['month', 'region_code']


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'origin_address', 'destination_address', 'recommended_bucket', 'created_at']
    list_filter = ['recommended_bucket', 'created_at']
    search_fields = ['user__email', 'origin_address', 'destination_address']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'planned_departure', 'started_at', 'arrived_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email']


@admin.register(TripStatusLog)
class TripStatusLogAdmin(admin.ModelAdmin):
    list_display = ['trip', 'status', 'logged_at']
    list_filter = ['status', 'logged_at']
