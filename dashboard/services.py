
from django.contrib.auth import get_user_model
from django.db.models import Q

from jobs.models import Job
from complaints.models import Complaint
from django.utils import timezone
from bookings.models import (
    ServiceRequest,
    Appointment,
    HandymanProfileRequest,
)
from django.db.models import Sum
from payments.models import Quotation, Payment

def get_admin_dashboard_stats():
    User = get_user_model()

    return {
        # User statistics
        'total_customers': User.objects.filter(
            role='customer',
            is_active=True,
            is_superuser=False
        ).count(),

        'total_handymen': User.objects.filter(
            role='handyman',
            is_active=True
        ).count(),

        'total_admins': User.objects.filter(
            Q(role='admin') | Q(is_superuser=True),
            is_staff=True,
            is_active=True
        ).count(),

        # Job statistics
        'total_jobs': Job.objects.count(),
        'assigned_jobs': Job.objects.filter(
            status=Job.ASSIGNED
        ).count(),
        'in_progress_jobs': Job.objects.filter(
            status=Job.IN_PROGRESS
        ).count(),
        'completed_jobs': Job.objects.filter(
            status=Job.COMPLETED
        ).count(),
        'cancelled_jobs': Job.objects.filter(
            status=Job.CANCELLED
        ).count(),

        # Complaint statistics
        'total_complaints': Complaint.objects.count(),
        'pending_complaints': Complaint.objects.filter(
            status=Complaint.PENDING
        ).count(),
        'in_progress_complaints': Complaint.objects.filter(
            status=Complaint.IN_PROGRESS
        ).count(),
        'resolved_complaints': Complaint.objects.filter(
            status=Complaint.RESOLVED
        ).count(),


        # Booking statistics
        'total_service_requests': ServiceRequest.objects.count(),

        'new_service_requests': ServiceRequest.objects.filter(
            status__in=['requested', ServiceRequest.STATUS_SUBMITTED]
        ).count(),

        'reviewing_requests': ServiceRequest.objects.filter(
            status=ServiceRequest.STATUS_REVIEWING
        ).count(),

        'booked_requests': ServiceRequest.objects.filter(
            status=ServiceRequest.STATUS_BOOKED
        ).count(),

        # Appointment statistics
        'total_appointments': Appointment.objects.count(),

        'pending_appointments': Appointment.objects.filter(
            status=Appointment.STATUS_PENDING
        ).count(),

        'confirmed_appointments': Appointment.objects.filter(
            status=Appointment.STATUS_CONFIRMED
        ).count(),

        'upcoming_appointments': Appointment.objects.filter(
            status=Appointment.STATUS_CONFIRMED,
            appointment_date__gte=timezone.localdate()
        ).count(),

        # Handyman profile requests
        'pending_profile_requests': HandymanProfileRequest.objects.filter(
            status=HandymanProfileRequest.STATUS_PENDING
        ).count(),


        # Quotation statistics
        'total_quotations': Quotation.objects.count(),

        'draft_quotations': Quotation.objects.filter(
            status=Quotation.DRAFT
        ).count(),

        'sent_quotations': Quotation.objects.filter(
            status=Quotation.SENT
        ).count(),

        'accepted_quotations': Quotation.objects.filter(
            status=Quotation.ACCEPTED
        ).count(),

        'declined_quotations': Quotation.objects.filter(
            status=Quotation.DECLINED
        ).count(),

        # Payment statistics
        'total_payments': Payment.objects.count(),

        'total_amount_received': (
            Payment.objects.aggregate(
                total=Sum('amount')
            )['total'] or 0
        ),

        'awaiting_payment': Quotation.objects.filter(
            status=Quotation.ACCEPTED,
            payment__isnull=True
        ).count(),


    }
