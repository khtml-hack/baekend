from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class CongestionIndex(models.Model):
    month = models.CharField(max_length=6)  # YYYYMM
    region_code = models.CharField(max_length=20, null=True, blank=True)
    T0 = models.DecimalField(max_digits=5, decimal_places=2)  # 06:00~08:00
    T1 = models.DecimalField(max_digits=5, decimal_places=2)  # 08:00~10:00
    T2 = models.DecimalField(max_digits=5, decimal_places=2)  # 17:00~19:00
    T3 = models.DecimalField(max_digits=5, decimal_places=2)  # 19:00~21:00
    version = models.CharField(max_length=20, default='v1')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('month', 'region_code', 'version')
        ordering = ['-month']

    def __str__(self):
        return f"{self.month} - {self.region_code or 'ALL'} ({self.version})"


class Recommendation(models.Model):
    BUCKET_CHOICES = [
        ('T0', 'T0 (06:00-08:00)'),
        ('T1', 'T1 (08:00-10:00)'),
        ('T2', 'T2 (17:00-19:00)'),
        ('T3', 'T3 (19:00-21:00)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    origin_address = models.CharField(max_length=255)
    destination_address = models.CharField(max_length=255)
    recommended_bucket = models.CharField(max_length=2, choices=BUCKET_CHOICES)
    window_start = models.TimeField()
    window_end = models.TimeField()
    expected_duration_min = models.PositiveIntegerField(null=True, blank=True)
    expected_congestion_level = models.SmallIntegerField(null=True, blank=True)
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.origin_address} → {self.destination_address}"


class Trip(models.Model):
    STATUS_CHOICES = [
        ('planned', '계획됨'),
        ('ongoing', '진행중'),
        ('arrived', '도착'),
        ('cancelled', '취소됨'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    recommendation = models.ForeignKey(Recommendation, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    planned_departure = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    predicted_duration_min = models.PositiveIntegerField(null=True, blank=True)
    actual_duration_min = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.status} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class TripStatusLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=20)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_at']

    def __str__(self):
        return f"Trip {self.trip.id} - {self.status} at {self.logged_at}"
