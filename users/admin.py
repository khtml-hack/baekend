from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'nickname', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'username', 'nickname']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    
    # superuser 생성 시 필수 필드 설정
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # 새 사용자 생성 시
            form.base_fields['is_staff'].initial = True
            form.base_fields['is_superuser'].initial = True
        return form