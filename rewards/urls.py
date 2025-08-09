from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('', views.WalletView.as_view(), name='wallet'),
    path('transactions/', views.WalletTransactionsView.as_view(), name='transactions'),
    path('preview/<int:trip_id>/', views.preview_departure_reward, name='preview_departure_reward'),
    path('summary/', views.reward_summary, name='reward_summary'),
]
