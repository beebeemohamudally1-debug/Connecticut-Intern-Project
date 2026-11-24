from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    # administrator: labour estimates
    path('estimates/', views.estimate_list, name='estimate_list'),
    path('estimates/<int:pk>/action/', views.estimate_action, name='estimate_action'),
    # administrator: quotations
    path('quotations/', views.quotation_list, name='quotation_list'),
    path('quotations/new/<int:request_id>/', views.quotation_create, name='quotation_create'),
    path('quotations/<int:pk>/', views.quotation_detail_admin, name='quotation_detail_admin'),
    path('quotations/<int:pk>/edit/', views.quotation_edit, name='quotation_edit'),
    path('quotations/<int:pk>/send/', views.quotation_send, name='quotation_send'),
    path('quotations/<int:pk>/cancel/', views.quotation_cancel, name='quotation_cancel'),
    path('quotations/<int:quotation_id>/pay/', views.payment_record, name='payment_record'),
    # administrator: materials
    path('materials/', views.admin_materials, name='admin_materials'),
    path('materials/quotations/', views.material_quotation_list, name='material_quotation_list'),
    path('materials/<int:pk>/action/', views.material_request_action, name='material_request_action'),
    path('receipts/<int:pk>/action/', views.receipt_action, name='receipt_action'),
    # handyman
    path('handyman/estimates/', views.my_estimates, name='my_estimates'),
    path('handyman/estimates/new/<int:request_id>/', views.estimate_submit, name='estimate_submit'),
    path('handyman/estimates/<int:pk>/revise/', views.estimate_resubmit, name='estimate_resubmit'),
    path('handyman/materials/', views.my_materials, name='my_materials'),
    path('handyman/materials/new/<int:request_id>/', views.material_request_submit, name='material_request_submit'),
    path('handyman/materials/<int:pk>/receipt/', views.receipt_upload, name='receipt_upload'),
    # customer
    path('my/quotations/', views.my_quotations, name='my_quotations'),
    path('my/quotations/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    path('my/payments/', views.payment_history, name='payment_history'),
]