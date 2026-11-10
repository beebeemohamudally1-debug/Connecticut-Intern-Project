from django.urls import path
from django.views.generic import TemplateView


def page(name):
    return TemplateView.as_view(template_name=f'payments/{name}.html')


urlpatterns = [
    path('admin-record-payment/', page('admin_record_payment')),
    path('admin-dashboard/', page('admin_dashboard')),
    path('customer-invoice/', page('customer_invoice')),
    path('customer-receipt/', page('customer_receipt')),
    path('handyman-earnings/', page('handyman_earnings')),
]