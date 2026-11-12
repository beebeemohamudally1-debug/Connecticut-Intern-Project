from django.contrib import admin
from django.utils import timezone

from .models import (
    ServiceRequest,
)


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
