from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UserConsent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consents')
    consent_type = models.CharField(max_length=50)
    consent_status = models.BooleanField()
    consented_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'consent_type')
        ordering = ['-consented_at']

    def __str__(self):
        return f"{self.user.email} - {self.consent_type}: {self.consent_status}"


class UserRoute(models.Model):
    ROUTE_TYPE_CHOICES = [
        ('집', '집'),
        ('직장', '직장'),
        ('학교', '학교'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='routes')
    route_type = models.CharField(max_length=20, choices=ROUTE_TYPE_CHOICES)
    address = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'route_type')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.route_type}: {self.address}"
