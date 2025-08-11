from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('token/', views.LoginView.as_view(), name='token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', views.MeView.as_view(), name='profile'),
    path('me/', views.MeView.as_view(), name='me'),
    path('nickname/', views.NicknameView.as_view(), name='nickname'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]

