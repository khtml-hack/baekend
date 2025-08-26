from datetime import datetime, timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Recommendation, Trip, TripStatusLog
from .serializers import (
    RecommendationRequestSerializer, 
    RecommendationSerializer,
    TripSerializer,
    RecommendationCreateResponseSerializer,
    TripStartResponseSerializer,
    TripArriveResponseSerializer,
    OptimalTravelTimeResponseSerializer,
)
from .services.recommend_service import create_recommendation
from .services.congestion_service import get_optimal_time_window
from rewards.utils import reward_for_trip_completion
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view, OpenApiResponse
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    post=extend_schema(
        tags=["Trips"],
        summary="여행 추천 생성 (2개 옵션 제공)",
        request=RecommendationRequestSerializer,
        responses={201: RecommendationCreateResponseSerializer}
    )
)
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


@extend_schema(
    tags=["Trips"],
    summary="여행 시작",
    responses={201: TripStartResponseSerializer}
)
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
    
    # 출발 시 보상은 제거 - 도착 시에만 보상 지급
    
    # 응답 데이터 구성
    response_data = TripSerializer(trip).data
    response_data['message'] = '여행이 시작되었습니다. 도착 시 보상을 받을 수 있습니다.'
    
    return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Trips"],
    summary="여행 완료 (보상 지급)",
    responses={200: TripArriveResponseSerializer, 400: OpenApiResponse(description="잘못된 상태")}
)
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
    response_data['completion_reward'] = completion_reward
    
    return Response(response_data)


@extend_schema_view(
    get=extend_schema(
        tags=["Trips"],
        summary="나의 여행 이력 조회",
        responses={200: TripSerializer(many=True)}
    )
)
class TripHistoryView(generics.ListAPIView):
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Trip.objects.filter(user=self.request.user)


@extend_schema(
    tags=["Trips"],
    summary="정확한 최적 출발 시각 추천 (1분 단위)",
    description="현재 시간 기준 window_hours 이내에서 1분 단위로 스캔하여 최적 출발 시각을 제공합니다.",
    parameters=[
        OpenApiParameter('window_hours', OpenApiTypes.INT, description='검색할 시간 범위 (기본: 2시간)'),
        OpenApiParameter('current_time', OpenApiTypes.STR, description='기준 시간 (YYYY-MM-DD HH:MM 형식, 미제공시 현재 시간)'),
        OpenApiParameter('location', OpenApiTypes.STR, description='목적지 (혼잡도 보정용, 예: gangnam, hongdae, myeongdong)'),
    ],
    responses={200: OptimalTravelTimeResponseSerializer}
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_optimal_travel_time(request):
    """현재 시간 기준 2시간 내 최적 여행 시간 추천 API (정확한 한 시각, 분 단위)"""
    try:
        window_hours = int(request.GET.get('window_hours', 2))
        current_time_str = request.GET.get('current_time')
        location = request.GET.get('location', 'default')

        current_time = None
        if current_time_str:
            try:
                current_time = datetime.strptime(current_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                return Response({'error': '시간 형식이 올바르지 않습니다. YYYY-MM-DD HH:MM 형식을 사용하세요.'}, status=status.HTTP_400_BAD_REQUEST)

        optimal_info = get_optimal_time_window(current_time=current_time, window_hours=window_hours, location=location)
        if not optimal_info:
            return Response({'error': '최적 시간을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        response_data = {
            'optimal_time': optimal_info['optimal_time'],  # {'time': 'HH:MM', 'congestion_score': float}
            'alternative_times': optimal_info['alternative_times'],  # [{time, congestion_score}]
            'search_window': optimal_info['search_window'],  # {start, end}
            'location': location,
            'precision': '1분 단위',
            'analyzed_minutes': optimal_info['all_minutes_analyzed']
        }
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'최적 시간 추천 중 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
