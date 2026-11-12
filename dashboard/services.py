
from django.contrib.auth import get_user_model
from django.db.models import Q

from jobs.models import Job
from complaints.models import Complaint


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
    }
