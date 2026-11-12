from django.contrib import admin
from django.utils import timezone

from .models import (
    ServiceRequest,
    ServiceRequestAssignment,
)


class ServiceRequestAssignmentInline(admin.TabularInline):
    model = ServiceRequestAssignment
    extra = 0
    fields = ('handyman', 'status', 'sent_by', 'sent_at', 'responded_at', 'response_note')
    readonly_fields = ('sent_at',)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'customer',
        'service_category',
        'preferred_date',
        'preferred_slot',
        'status',
        'full_payment_received_at',
    )
    list_filter = ('status', 'service_category', 'preferred_slot', 'preferred_date')
    search_fields = (
        'reference',
        'customer__username',
        'customer__email',
        'service_category',
        'problem_description',
        'contact_name',
        'contact_phone',
    )
    readonly_fields = ('reference', 'created_at', 'updated_at')
    inlines = (ServiceRequestAssignmentInline,)


@admin.register(ServiceRequestAssignment)
class ServiceRequestAssignmentAdmin(admin.ModelAdmin):
    list_display = ('service_request', 'handyman', 'status', 'sent_at', 'responded_at')
    list_filter = ('status', 'sent_at', 'responded_at')
    search_fields = ('service_request__reference', 'handyman__username', 'response_note')
    readonly_fields = ('sent_at',)
