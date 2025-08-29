from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'nickname', 'zone_code', 'zone_name', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'username', 'nickname', 'zone_code', 'zone_name']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'zone_code']
    
    # superuser 생성 시 필수 필드 설정
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # 새 사용자 생성 시
            form.base_fields['is_staff'].initial = True
            form.base_fields['is_superuser'].initial = True
        return form

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('개인정보', {'fields': ('nickname', 'address', 'address_lat', 'address_lng')}),
        ('구역', {'fields': ('zone_code', 'zone_name')}),
        ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )