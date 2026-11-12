
from django.http import JsonResponse
from dashboard.permissions import role_required
from django.shortcuts import render

@role_required('admin')
def job_summary_report(request):
    return JsonResponse({
        'report': 'Job Summary Report',
        'status': 'ready',
        'message': 'Report structure created. Job data will be added later.'
    })


@role_required('admin')
def job_summary_report(request):
    context = {
        'report_title': 'Job Summary Report',
        'jobs': [],
        'total_jobs': 0,
    }

    return render(
        request,
        'reports/job_summary.html',
        context
    )
