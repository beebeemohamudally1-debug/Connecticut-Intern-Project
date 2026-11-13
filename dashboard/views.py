from django.shortcuts import render

from .permissions import role_required
from .services import (
    get_admin_dashboard_stats,
    get_recent_activities,
    get_admin_pending_tasks,
    get_admin_payment_details,
)


@role_required('handyman')
def handyman_dashboard(request):
    return render(request, 'dashboard/handyman_dashboard.html')


@role_required('handyman')
def assigned_jobs(request):
    return render(request, 'dashboard/handyman_assigned_jobs.html')


@role_required('handyman')
def job_requests(request):
    return render(request, 'dashboard/handyman_job_requests.html')


@role_required('handyman')
def job_tracking(request):
    return render(request, 'dashboard/handyman_job_tracking.html')


@role_required('handyman')
def job_in_progress(request):
    return render(request, 'dashboard/handyman_job_in_progress.html')


@role_required('handyman')
def job_completed(request):
    return render(request, 'dashboard/handyman_job_completed.html')


@role_required('handyman')
def report_customer(request):
    return render(request, 'dashboard/handyman_report_customer.html')


@role_required('handyman')
def notifications(request):
    return render(request, 'dashboard/handyman_notifs.html')


@role_required('customer')
def customer_dashboard(request):
    return render(request, 'dashboard/customer_dashboard.html')


@role_required('admin')
def admin_dashboard(request):
    stats = get_admin_dashboard_stats()
    activities = get_recent_activities()
    pending = get_admin_pending_tasks()
    payment_details = get_admin_payment_details()

    return render(
        request,
        'dashboard/admin_dashboard.html',
        {
            'stats': stats,
            'activities': activities,
            **pending,
            **payment_details,
        }
    )