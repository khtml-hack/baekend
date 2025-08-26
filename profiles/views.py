from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .models import UserConsent, UserRoute
from .serializers import UserConsentSerializer, UserRouteSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view


@extend_schema_view(
    post=extend_schema(
        tags=["Profiles"],
        summary="동의 항목 생성",
        responses={201: UserConsentSerializer}
    )
)
class UserConsentCreateView(generics.CreateAPIView):
    serializer_class = UserConsentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserConsent.objects.filter(user=self.request.user)


@extend_schema_view(
    get=extend_schema(
        tags=["Profiles"],
        summary="자주 쓰는 경로 목록",
        responses={200: UserRouteSerializer(many=True)}
    ),
    post=extend_schema(
        tags=["Profiles"],
        summary="자주 쓰는 경로 추가",
        responses={201: UserRouteSerializer}
    )
)
class UserRouteListCreateView(generics.ListCreateAPIView):
    serializer_class = UserRouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserRoute.objects.filter(user=self.request.user)


@extend_schema_view(
    get=extend_schema(
        tags=["Profiles"],
        summary="경로 상세"
    ),
    patch=extend_schema(
        tags=["Profiles"],
        summary="경로 수정"
    ),
    delete=extend_schema(
        tags=["Profiles"],
        summary="경로 삭제"
    ),
)
class UserRouteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserRouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserRoute.objects.filter(user=self.request.user)
