from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('', views.WalletView.as_view(), name='wallet'),
    path('transactions/', views.WalletTransactionsView.as_view(), name='transactions'),
]
