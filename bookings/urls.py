from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    # Customer requests and appointment responses
    path('my/requests/', views.my_requests, name='my_requests'),
    path('my/requests/new/', views.create_request, name='create_request'),
    path('my/requests/<int:pk>/', views.my_request_detail, name='my_request_detail'),
    path('my/requests/<int:pk>/choose-handyman/', views.choose_another_handyman, name='choose_handyman'),
    path('my/appointments/', views.my_appointments, name='my_appointments'),
    path('my/appointments/<int:pk>/respond/', views.appointment_respond, name='appointment_respond'),
    # Handyman request inbox
    path('handyman/requests/', views.handyman_requests, name='handyman_requests'),
    path('handyman/requests/<int:pk>/respond/', views.handyman_respond, name='handyman_respond'),
    # Admin portal - Manage Service Requests
    path('admin/requests/', views.admin_requests, name='admin_requests'),
    path('admin/requests/<int:pk>/', views.admin_request_detail, name='admin_request_detail'),
    path('admin/requests/<int:pk>/forward/', views.admin_forward_request, name='admin_forward_request'),
    path('admin/requests/<int:pk>/notify-rejection/', views.admin_notify_rejection, name='admin_notify_rejection'),
]
