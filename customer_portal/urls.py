from django.urls import path

from . import views

app_name = 'customer_portal'

urlpatterns = [
    path('requests/', views.requests_list, name='requests'),
    path('requests/new/', views.new_request, name='new_request'),
    path('requests/<int:pk>/submitted/', views.request_submitted, name='request_submitted'),
    path('appointments/', views.appointments, name='appointments'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read-all/', views.notifications_read_all, name='notifications_read_all'),
    path('notifications/<int:pk>/open/', views.notification_open, name='notification_open'),
    path('profile/', views.profile, name='profile'),
    path('history/', views.history, name='history'),
]
