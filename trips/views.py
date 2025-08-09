from datetime import datetime, timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Recommendation, Trip, TripStatusLog
from .serializers import (
    RecommendationRequestSerializer, 
    RecommendationSerializer,
    TripSerializer
)
from .services.recommend_service import create_recommendation
from .services.congestion_service import get_optimal_time_window
from rewards.utils import reward_for_trip_departure, reward_for_trip_completion
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class RecommendationCreateView(generics.CreateAPIView):
    serializer_class = RecommendationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 추천 생성
        result = create_recommendation(
            user=request.user,
            origin_address=serializer.validated_data['origin_address'],
            destination_address=serializer.validated_data['destination_address'],
            region_code=serializer.validated_data.get('region_code')
        )
        
        return Response(result, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_trip(request, recommendation_id):
    """여행 시작"""
    recommendation = get_object_or_404(
        Recommendation, 
        id=recommendation_id, 
        user=request.user
    )
    
    # 계획된 출발시간을 window_start로 설정
    planned_departure = datetime.combine(
        datetime.now().date(),
        recommendation.window_start
    )
    
    # Trip 생성
    trip = Trip.objects.create(
        user=request.user,
        recommendation=recommendation,
        status='ongoing',
        planned_departure=planned_departure,
        started_at=datetime.now(),
        predicted_duration_min=recommendation.expected_duration_min
    )
    
    # 상태 로그 생성
    TripStatusLog.objects.create(
        trip=trip,
        status='ongoing'
    )
    
    # AI 추천 기반 출발 보상 지급
    departure_reward = reward_for_trip_departure(request.user, trip)
    
    # 응답 데이터 구성
    response_data = TripSerializer(trip).data
    response_data['departure_reward'] = departure_reward
    
    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def arrive_trip(request, trip_id):
    """여행 완료"""
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    
    if trip.status != 'ongoing':
        return Response(
            {'error': '진행 중인 여행만 완료할 수 있습니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 도착 처리
    arrived_at = datetime.now()
    trip.arrived_at = arrived_at
    trip.status = 'arrived'
    
    # 실제 소요시간 계산
    if trip.started_at:
        duration = arrived_at - trip.started_at
        trip.actual_duration_min = int(duration.total_seconds() / 60)
    
    trip.save()
    
    # 상태 로그 생성
    TripStatusLog.objects.create(
        trip=trip,
        status='arrived'
    )
    
    # 여행 완료 보상 지급
    completion_reward = reward_for_trip_completion(request.user, trip)
    
    # 응답 데이터 구성
    response_data = TripSerializer(trip).data
    response_data['completion_reward'] = {
        'success': True,
        'transaction_id': completion_reward.id,
        'amount': completion_reward.amount,
        'description': completion_reward.description
    }
    
    return Response(response_data)


class TripHistoryView(generics.ListAPIView):
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Trip.objects.filter(user=self.request.user)


@extend_schema(
    description="현재 시간 기준 2시간 내 최적 여행 시간 추천",
    parameters=[
        OpenApiParameter('window_hours', OpenApiTypes.INT, description='검색할 시간 범위 (기본: 2시간)'),
        OpenApiParameter('current_time', OpenApiTypes.STR, description='기준 시간 (YYYY-MM-DD HH:MM 형식, 미제공시 현재 시간)'),
        OpenApiParameter('location', OpenApiTypes.STR, description='목적지 (혼잡도 보정용, 예: gangnam, hongdae, myeongdong)'),
    ]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_optimal_travel_time(request):
    """현재 시간 기준 2시간 내 최적 여행 시간 추천 API"""
    try:
        # 요청 파라미터 수집
        window_hours = int(request.GET.get('window_hours', 2))
        current_time_str = request.GET.get('current_time')
        location = request.GET.get('location', 'default')
        
        # 기준 시간 파싱
        current_time = None
        if current_time_str:
            try:
                current_time = datetime.strptime(current_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                return Response(
                    {'error': '시간 형식이 올바르지 않습니다. YYYY-MM-DD HH:MM 형식을 사용하세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 최적 시간 추천
        optimal_time_info = get_optimal_time_window(
            current_time=current_time,
            window_hours=window_hours,
            location=location
        )
        
        # 시간 정보를 문자열로 변환하여 JSON 직렬화 가능하게 만들기
        def format_time_info(window):
            if window and 'slot_start' in window:
                window['slot_start'] = window['slot_start'].strftime('%Y-%m-%d %H:%M:%S')
                window['slot_end'] = window['slot_end'].strftime('%Y-%m-%d %H:%M:%S')
            return window
        
        if optimal_time_info['optimal_window']:
            optimal_time_info['optimal_window'] = format_time_info(optimal_time_info['optimal_window'])
        
        optimal_time_info['alternatives'] = [format_time_info(alt) for alt in optimal_time_info['alternatives']]
        
        return Response(optimal_time_info, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'최적 시간 추천 중 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
