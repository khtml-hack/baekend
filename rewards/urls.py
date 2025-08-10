from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('', views.WalletView.as_view(), name='wallet'),
    path('transactions/', views.WalletTransactionsView.as_view(), name='transactions'),
    # path('preview/<int:trip_id>/', views.preview_departure_reward, name='preview_departure_reward'),  # 출발 시 보상 비활성화
    path('summary/', views.reward_summary, name='reward_summary'),
]
