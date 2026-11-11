from django.shortcuts import render
from .permissions import role_required
from .services import get_admin_dashboard_stats

@role_required('handyman')
def handyman_dashboard(request):
    return render(
        request,
        'dashboard/handyman_dashboard.html'
    )


@role_required('customer')
def customer_dashboard(request):
    return render(
        request,
        'dashboard/customer_dashboard.html'
    )


@role_required('admin')
def admin_dashboard(request):
    stats = get_admin_dashboard_stats()

    return render(
        request,
        'dashboard/admin_dashboard.html',
        {'stats': stats}
    )
    
