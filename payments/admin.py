from django.contrib import admin
from .models import Quotation, Payment

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'quotation', 'amount', 'method', 'date_received', 'recorded_by')
