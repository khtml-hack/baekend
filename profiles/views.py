from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .models import UserConsent, UserRoute
from .serializers import UserConsentSerializer, UserRouteSerializer


class UserConsentCreateView(generics.CreateAPIView):
    serializer_class = UserConsentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserConsent.objects.filter(user=self.request.user)


class UserRouteListCreateView(generics.ListCreateAPIView):
    serializer_class = UserRouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserRoute.objects.filter(user=self.request.user)


class UserRouteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserRouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserRoute.objects.filter(user=self.request.user)
