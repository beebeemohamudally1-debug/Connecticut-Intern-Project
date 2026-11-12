
from datetime import date

from django.shortcuts import render
from django.db.models import Count, Q
from dashboard.permissions import role_required
from jobs.models import Job


@role_required('admin')
def job_summary_report(request):

    jobs = Job.objects.select_related(
        'customer',
        'handyman'
    ).all()

    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    if status in dict(Job.STATUS_CHOICES):
        jobs = jobs.filter(status=status)

    try:
        if start_date:
            jobs = jobs.filter(
                created_at__date__gte=date.fromisoformat(start_date)
            )
        if end_date:
            jobs = jobs.filter(
                created_at__date__lte=date.fromisoformat(end_date)
            )
    except ValueError:
        pass

    stats = jobs.aggregate(
        total_jobs=Count('id'),
        assigned_jobs=Count('id', filter=Q(status=Job.ASSIGNED)),
        in_progress_jobs=Count('id', filter=Q(status=Job.IN_PROGRESS)),
        completed_jobs=Count('id', filter=Q(status=Job.COMPLETED)),
        cancelled_jobs=Count('id', filter=Q(status=Job.CANCELLED)),
    )

    context = {
        'report_title': 'Job Summary Report',
        'jobs': jobs,
        'status_choices': Job.STATUS_CHOICES,
        'selected_status': status,
        'start_date': start_date,
        'end_date': end_date,
        **stats,
    }

    return render(request, 'reports/job_summary.html', context)
