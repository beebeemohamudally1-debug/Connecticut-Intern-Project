from django.urls import path
from . import admin_views as views

app_name = 'accounts_admin'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('users/', views.users, name='users'),
    path('users/customer/', views.customer_detail, name='customer_detail'),
    path('users/customer/suspended/', views.suspended_customer, name='suspended_customer'),
    path('users/handyman/', views.handyman_profile, name='handyman_profile'),
    path('users/handyman/suspended/', views.suspended_handyman, name='suspended_handyman'),
    path('users/handyman/documents/', views.handyman_documents, name='handyman_documents'),
    path('users/handyman/verify/', views.handyman_verify, name='handyman_verify'),
    path('notifications/', views.notifications, name='notifications'),
]