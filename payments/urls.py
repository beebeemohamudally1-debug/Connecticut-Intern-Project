from django.urls import path
from django.views.generic import TemplateView
from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    # administrator
    path('quotations/', views.quotation_list, name='quotation_list'),
    path('quotations/new/<int:request_id>/', views.quotation_create, name='quotation_create'),
    path('quotations/<int:pk>/send/', views.quotation_send, name='quotation_send'),
    path('quotations/<int:quotation_id>/pay/', views.payment_record, name='payment_record'),
    # customer
    path('my/quotations/', views.my_quotations, name='my_quotations'),
    path('my/quotations/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    path('my/payments/', views.payment_history, name='payment_history'),
]
