
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


def get_recent_activities(limit=10):
    """Return the latest activities for the Admin Dashboard."""
    activities = []

    # Recent service requests
    for request in ServiceRequest.objects.order_by('-created_at')[:limit]:
        activities.append({
            'kind': 'request',
            'text': f'Service request {request.reference} - {request.status}',
            'time': request.created_at,
        })

    # Recent quotations
    for quote in Quotation.objects.select_related(
        'request'
    ).order_by('-created_at')[:limit]:
        activities.append({
            'kind': 'quotation',
            'text': f'Quotation for request {quote.request.reference} - {quote.status}',
            'time': quote.created_at,
        })

    # Recent payments
    for payment in Payment.objects.select_related(
        'quotation__request'
    ).order_by('-created_at')[:limit]:
        activities.append({
            'kind': 'payment',
            'text': (
                f'Payment of MUR {payment.amount} received '
                f'for request {payment.quotation.request.reference}'
            ),
            'time': payment.created_at,
        })

    # Recent complaints
    for complaint in Complaint.objects.order_by('-created_at')[:limit]:
        activities.append({
            'kind': 'complaint',
            'text': f'Complaint {complaint.reference} - {complaint.status}',
            'time': complaint.created_at,
        })

    # Recent appointments
    for appointment in Appointment.objects.select_related(
        'service_request'
    ).order_by('-created_at')[:limit]:
        activities.append({
            'kind': 'appointment',
            'text': (
                f'Appointment for request '
                f'{appointment.service_request.reference} - '
                f'{appointment.status}'
            ),
            'time': appointment.created_at,
        })

    # Combine and sort activities by newest first
    activities.sort(
        key=lambda activity: activity['time'],
        reverse=True
    )

    return activities[:limit]


def get_admin_pending_tasks():
    """Return tasks that require administrator attention."""

    stats = get_admin_dashboard_stats()

    task_definitions = [
        {
            'key': 'requests',
            'cat': 'requests',
            'title': 'New Service Requests',
            'text': 'Service requests waiting for review',
            'count': stats['new_service_requests'],
            'url': '#',
        },
        {
            'key': 'appointments',
            'cat': 'appointments',
            'title': 'Pending Appointments',
            'text': 'Appointments waiting for confirmation',
            'count': stats['pending_appointments'],
            'url': '#',
        },
        {
            'key': 'payments',
            'cat': 'payments',
            'title': 'Payments Awaiting Collection',
            'text': 'Accepted quotations without recorded payment',
            'count': stats['awaiting_payment'],
            'url': '/payments/admin-record-payment/',
        },
        {
            'key': 'complaints',
            'cat': 'complaints',
            'title': 'Pending Complaints',
            'text': 'Complaints waiting for administrator action',
            'count': stats['pending_complaints'],
            'url': '/complaints/',
        },
        {
            'key': 'skills',
            'cat': 'skills',
            'title': 'Handyman Profile Requests',
            'text': 'Profile changes waiting for approval',
            'count': stats['pending_profile_requests'],
            'url': '#',
        },
        {
            'key': 'requests',
            'cat': 'quotations',
            'title': 'Draft Quotations',
            'text': 'Quotations that have not been sent',
            'count': stats['draft_quotations'],
            'url': '#',
        },
    ]

    tasks = [
        task for task in task_definitions
        if task['count'] > 0
    ]

    categories = [
        {
            'key': task['cat'],
            'name': task['title'],
            'count': task['count'],
        }
        for task in tasks
    ]

    return {
        'tasks': tasks,
        'tasks_total': sum(task['count'] for task in tasks),
        'categories': categories,
    }


def get_admin_payment_details(limit=10):
    """Return accepted quotations awaiting offline payment."""

    unpaid = Quotation.objects.filter(
        status=Quotation.ACCEPTED,
        payment__isnull=True
    ).exclude(
        request__status='cancelled'
    ).select_related(
        'request__customer'
    ).order_by('-created_at')

    summary = unpaid.aggregate(
        total=Sum('total_amount')
    )

    payment_actions = []

    for quotation in unpaid[:limit]:
        customer = quotation.request.customer

        payment_actions.append({
            'ref': f'Q-{quotation.pk}',
            'customer': customer.get_full_name() or customer.username,
            'amount': quotation.total_amount,
            'issue': 'Payment not recorded',
            'status': 'Awaiting payment',
            'tone': 'warning',
            'action': 'Review',
        })

    return {
        'payment_summary': [
            {
                'label': 'Awaiting Payment',
                'value': unpaid.count(),
            },
            {
                'label': 'Outstanding Amount (MUR)',
                'value': summary['total'] or 0,
            },
            {
                'label': 'Payments Received',
                'value': Payment.objects.count(),
            },
        ],
        'payment_actions': payment_actions,
        'payments_url': '/payments/admin-record-payment/',
    }
