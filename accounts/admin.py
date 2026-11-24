from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import HandymanProfile, User

PROFILE_FIELDS = ('role', 'phone', 'additional_names', 'address', 'region',
                  'is_suspended', 'must_change_password')


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (('HandyConnect profile', {'fields': PROFILE_FIELDS}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (('HandyConnect profile', {'fields': ('role', 'phone')}),)
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active', 'is_suspended')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'is_suspended')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')


@admin.register(HandymanProfile)
class HandymanProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at')
    list_filter = ('status', 'categories', 'service_areas')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    filter_horizontal = ('categories', 'services', 'skills', 'service_areas')
    actions = ['approve_selected', 'reject_selected']

    @admin.action(description='Approve selected handymen')
    def approve_selected(self, request, queryset):
        queryset.update(status=HandymanProfile.STATUS_ACTIVE, rejection_reason='')

    @admin.action(description='Reject selected handymen')
    def reject_selected(self, request, queryset):
        queryset.update(status=HandymanProfile.STATUS_REJECTED)