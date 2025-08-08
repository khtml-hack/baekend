from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from .models import Wallet, RewardTransaction
from .serializers import WalletSerializer, RewardTransactionSerializer


class TransactionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class WalletView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet

    def retrieve(self, request, *args, **kwargs):
        wallet = self.get_object()
        
        # 최근 10개 거래 포함
        recent_transactions = wallet.transactions.all()[:10]
        
        data = {
            'id': wallet.id,
            'balance': wallet.balance,
            'currency_code': wallet.currency_code,
            'created_at': wallet.created_at,
            'updated_at': wallet.updated_at,
            'recent_transactions': RewardTransactionSerializer(recent_transactions, many=True).data
        }
        
        return Response(data)


class WalletTransactionsView(generics.ListAPIView):
    serializer_class = RewardTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TransactionPagination

    def get_queryset(self):
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet.transactions.all()
