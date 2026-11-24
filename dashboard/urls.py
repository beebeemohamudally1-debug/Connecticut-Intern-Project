from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # existing routes from main
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('customer/', views.customer_dashboard, name='customer_dashboard'),
    path('handyman/', views.handyman_dashboard, name='handyman_dashboard'),

    # your handyman pages
    path('handyman/assigned-jobs/', views.assigned_jobs, name='assigned_jobs'),
    path('handyman/job-requests/', views.job_requests, name='job_requests'),
    path('handyman/job-in-progress/', views.job_in_progress, name='job_in_progress'),
    path('handyman/job-completed/', views.job_completed, name='job_completed'),
    path('handyman/report-customer/', views.report_customer, name='report_customer'),
    path('handyman/notifications/', views.notifications, name='notifications'),
]