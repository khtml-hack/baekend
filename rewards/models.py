from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.BigIntegerField(default=0)
    currency_code = models.CharField(max_length=3, default='LCL')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.balance} {self.currency_code}"

    class Meta:
        db_table = 'rewards_wallet'


class RewardTransaction(models.Model):
    TYPE_CHOICES = [
        ('earn', 'Earn'),
        ('spend', 'Spend'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    trip = models.ForeignKey('trips.Trip', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.BigIntegerField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.email} - {self.type} {self.amount} {self.wallet.currency_code}"

    class Meta:
        db_table = 'rewards_transaction'
        ordering = ['-created_at']
