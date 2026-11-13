from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Expose custom account fields and users in Django's admin site."""

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('HandyConnect profile', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('HandyConnect profile', {'fields': ('role', 'phone')}),
    )
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_staff',
        'is_active',
    )
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
