from rest_framework import serializers
from .models import Wallet, RewardTransaction


class RewardTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardTransaction
        fields = [
            'id', 'type', 'amount', 'description', 
            'created_at', 'trip'
        ]
        read_only_fields = ['id', 'created_at']


class WalletSerializer(serializers.ModelSerializer):
    recent_transactions = RewardTransactionSerializer(
        source='transactions', 
        many=True, 
        read_only=True
    )
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'balance', 'currency_code', 
            'created_at', 'updated_at', 'recent_transactions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WalletBalanceSerializer(serializers.ModelSerializer):
    """간단한 잔액 정보만 포함"""
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'currency_code']
        read_only_fields = ['id']
