from django.contrib import admin
from .models import Wallet, RewardTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'currency_code', 'created_at']
    list_filter = ['currency_code', 'created_at']
    search_fields = ['user__email', 'user__nickname']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RewardTransaction)
class RewardTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'type', 'amount', 'description', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['wallet__user__email', 'description']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('wallet__user')
