from django.urls import path
from . import views

urlpatterns = [
    path('', views.handyman_dashboard, name='handyman_dashboard'),
    path('assigned-jobs/', views.assigned_jobs, name='assigned_jobs'),
    path('job-requests/', views.job_requests, name='job_requests'),
    path('job-tracking/', views.job_tracking, name='job_tracking'),
    path('job-in-progress/', views.job_in_progress, name='job_in_progress'),
    path('job-completed/', views.job_completed, name='job_completed'),
    path('report-customer/', views.report_customer, name='report_customer'),
    path('notifications/', views.notifications, name='notifications'),
]