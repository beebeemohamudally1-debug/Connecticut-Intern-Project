from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    # Admin portal - Manage Service Requests
    path('admin/requests/', views.admin_requests, name='admin_requests'),
    path('admin/requests/<int:pk>/', views.admin_request_detail, name='admin_request_detail'),
]