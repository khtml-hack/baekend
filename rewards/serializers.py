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


class RewardSummarySerializer(serializers.Serializer):
    """보상 요약 정보"""
    current_balance = serializers.IntegerField()
    currency_code = serializers.CharField()
    total_earned = serializers.IntegerField()
    total_spent = serializers.IntegerField()
    transaction_count = serializers.IntegerField()
    recent_transactions = RewardTransactionSerializer(many=True)


class DepartureRewardPreviewSerializer(serializers.Serializer):
    """출발 보상 미리보기"""
    trip_id = serializers.IntegerField()
    expected_reward = serializers.IntegerField()
    base_reward = serializers.IntegerField()
    multiplier = serializers.FloatField()
    bonus_type = serializers.CharField()
    bonus_description = serializers.CharField()
    bucket_bonus = serializers.FloatField()
    recommendation_info = serializers.DictField()


class RewardResponseSerializer(serializers.Serializer):
    """보상 지급 응답"""
    success = serializers.BooleanField()
    transaction_id = serializers.IntegerField(required=False)
    reward_info = serializers.DictField(required=False)
    message = serializers.CharField()
    error = serializers.CharField(required=False)
