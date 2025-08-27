from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('recommend/', views.RecommendationCreateView.as_view(), name='recommend'),
    path('start/<int:recommendation_id>/', views.start_trip, name='start-trip'),
    path('arrive/<int:trip_id>/', views.arrive_trip, name='arrive-trip'),
    path('history/', views.TripHistoryView.as_view(), name='trip-history'),
    path('optimal-time/', views.get_optimal_travel_time, name='optimal-time'),
    path('arrive-by/', views.arrive_by, name='arrive-by'),
]
