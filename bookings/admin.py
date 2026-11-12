from django.contrib import admin
from django.utils import timezone

from .models import (
    ServiceRequest,
    ServiceRequestAssignment,
    Appointment,
    HandymanProfileRequest,
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


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'service_request',
        'handyman',
        'appointment_type',
        'appointment_date',
        'time_slot',
        'status',
    )
    list_filter = ('status', 'appointment_type', 'appointment_date', 'time_slot')
    search_fields = ('service_request__reference', 'handyman__username')
    readonly_fields = ('confirmed_by', 'confirmed_at', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if obj.status == Appointment.STATUS_CONFIRMED and not obj.confirmed_at:
            obj.confirmed_at = timezone.now()
            obj.confirmed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(HandymanProfileRequest)
class HandymanProfileRequestAdmin(admin.ModelAdmin):
    list_display = (
        'handyman',
        'request_type',
        'action',
        'current_value',
        'requested_value',
        'status',
        'submitted_at',
    )
    list_filter = ('request_type', 'action', 'status', 'submitted_at')
    search_fields = ('handyman__username', 'current_value', 'requested_value', 'reason')
    readonly_fields = ('submitted_at', 'reviewed_at')

    def save_model(self, request, obj, form, change):
        if obj.status in (HandymanProfileRequest.STATUS_APPROVED, HandymanProfileRequest.STATUS_REJECTED):
            if not obj.reviewed_at:
                obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
