from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('School role', {'fields': ('role', 'phone', 'is_blocked')}),
        ('Instructor spotlight (homepage)', {'fields': ('headline', 'location')}),
    )
    list_display = ('username', 'email', 'role', 'phone', 'is_blocked', 'is_active')
    list_filter = ('role', 'is_blocked', 'is_active')
    search_fields = ('username', 'email', 'phone')
