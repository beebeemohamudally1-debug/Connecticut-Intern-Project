from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('customer/', views.customer_dashboard, name='customer_dashboard'),
    path('handyman/', views.handyman_dashboard, name='handyman_dashboard'),
]