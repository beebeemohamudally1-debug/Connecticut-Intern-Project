from django.shortcuts import render

from .permissions import role_required
from .services import (
    get_admin_dashboard_stats,
    get_recent_activities,
    get_admin_pending_tasks,
    get_admin_payment_details,
)


def _handyman_page(name, template):
    @role_required('handyman')
    def view(request):
        return render(request, template)
    view.__name__ = name
    return view


handyman_dashboard = _handyman_page('handyman_dashboard', 'dashboard/handyman_dashboard.html')
assigned_jobs = _handyman_page('assigned_jobs', 'dashboard/handyman_assigned_jobs.html')
job_requests = _handyman_page('job_requests', 'dashboard/handyman_job_requests.html')
job_in_progress = _handyman_page('job_in_progress', 'dashboard/handyman_job_in_progress.html')
job_completed = _handyman_page('job_completed', 'dashboard/handyman_job_completed.html')
report_customer = _handyman_page('report_customer', 'dashboard/handyman_report_customer.html')
notifications = _handyman_page('notifications', 'dashboard/handyman_notifs.html')


@role_required('customer')
def customer_dashboard(request):
    return render(request, 'dashboard/customer_dashboard.html')


@role_required('admin')
def admin_dashboard(request):
    return render(
        request,
        'dashboard/admin_dashboard.html',
        {
            'stats': get_admin_dashboard_stats(),
            'activities': get_recent_activities(),
            **get_admin_pending_tasks(),
            **get_admin_payment_details(),
        },
    )