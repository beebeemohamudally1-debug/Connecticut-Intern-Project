from django.contrib import admin

from .models import (DocumentCounter, Invoice, InvoicePayment, LabourEstimate, MaterialPurchaseRequest, MaterialReceipt,
                     Payment, Quotation, Receipt)

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


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'invoice_type', 'request', 'total_amount', 'due_date', 'status')
    list_filter = ('invoice_type', 'status')
    search_fields = ('number',)
    readonly_fields = ('number',)


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'method', 'date_received', 'status', 'recorded_by')


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('number', 'invoice', 'issued_at')
    readonly_fields = ('number',)


admin.site.register(DocumentCounter)
