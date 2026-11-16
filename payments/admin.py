from django.contrib import admin

from .models import LabourEstimate, MaterialPurchaseRequest, MaterialReceipt, Payment, Quotation

admin.site.register(LabourEstimate)
admin.site.register(MaterialPurchaseRequest)
admin.site.register(MaterialReceipt)


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'quotation_type', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'quotation_type')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'quotation', 'amount', 'method', 'date_received', 'recorded_by')
