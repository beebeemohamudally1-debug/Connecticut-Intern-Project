from django.urls import path
from . import admin_appointments as appointments
from . import admin_views as views
from django.views.generic import TemplateView
from dashboard.permissions import role_required
app_name = 'accounts_admin'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('users/', views.users, name='users'),
    path('search/', views.search, name='search'),
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

    # TODO: BACKEND INTEGRATION
    # Temporary admin-only frontend routes.
    path('services/', role_required('admin')(TemplateView.as_view(template_name='services/manage_services.html')), name='manage_services'),
    path('services/add/', role_required('admin')(TemplateView.as_view(template_name='services/add_service.html')), name='add_service'),
    path('services/<int:service_id>/edit/', role_required('admin')(TemplateView.as_view(template_name='services/edit_service.html')), name='edit_service'),
    path('services/<int:service_id>/view/', role_required('admin')(TemplateView.as_view(template_name='services/view_service.html')), name='view_service'),
    path('services/handyman-requests/', role_required('admin')(TemplateView.as_view(template_name='services/handyman_requests.html')), name='handyman_requests'),
    path('services/handyman-requests/<int:request_id>/review/', role_required('admin')(TemplateView.as_view(template_name='services/review_request.html')), name='review_service_request'),
    path('complaints/<int:pk>/', views.complaint_case, name='complaint_case'),
    path('complaints/<int:pk>/customer/', views.complaint_conversation, {'who': 'customer'}, name='complaint_customer'),
    path('complaints/<int:pk>/handyman/', views.complaint_conversation, {'who': 'handyman'}, name='complaint_handyman'),
    path('complaints/<int:pk>/resolve/', views.complaint_resolve, name='complaint_resolve'),
    path('appointments/', appointments.appointments, name='appointments'),
    path('appointments/calendar/', appointments.appointment_calendar, name='appointment_calendar'),
    path('appointments/schedule/<str:kind>/', appointments.appointment_schedule, name='appointment_schedule'),
    path('appointments/<int:pk>/', appointments.appointment_detail, name='appointment_detail'),
    path('appointments/<int:pk>/reschedule/', appointments.appointment_reschedule, name='appointment_reschedule'),
]