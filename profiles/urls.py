from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('consents/', views.UserConsentCreateView.as_view(), name='consent-create'),
    path('routes/', views.UserRouteListCreateView.as_view(), name='route-list-create'),
    path('routes/<int:pk>/', views.UserRouteDetailView.as_view(), name='route-detail'),
]
