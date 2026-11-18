from django.urls import path
from . import admin_views as views

app_name = 'accounts_admin'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('users/', views.users, name='users'),
    path('users/customer/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('users/handyman/<int:pk>/', views.handyman_profile, name='handyman_profile'),
    path('users/handyman/documents/', views.handyman_documents, name='handyman_documents'),
    path('users/handyman/verify/', views.handyman_verify, name='handyman_verify'),
    path('notifications/', views.notifications, name='notifications'),
    path('work-progress/', views.work_progress, name='work_progress'),
    path('work-progress/<int:pk>/', views.job_progress, name='work_progress_job'),
    path('work-progress/<int:pk>/reports/', views.daily_reports, name='work_progress_reports'),
    path('work-progress/<int:pk>/evidence/', views.work_evidence, name='work_progress_evidence'),
    path('work-progress/<int:pk>/evidence/<int:report_pk>/', views.work_evidence, name='work_progress_report_evidence'),
    path('complaints/', views.complaint_queue, name='complaints'),
    path('complaints/<int:pk>/', views.complaint_case, name='complaint_case'),
    path('complaints/<int:pk>/customer/', views.complaint_conversation, {'who': 'customer'}, name='complaint_customer'),
    path('complaints/<int:pk>/handyman/', views.complaint_conversation, {'who': 'handyman'}, name='complaint_handyman'),
    path('complaints/<int:pk>/resolve/', views.complaint_resolve, name='complaint_resolve'),
]