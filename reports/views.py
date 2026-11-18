from datetime import date

from django.shortcuts import render
from django.db.models import Count, Prefetch, Q

from dashboard.permissions import role_required
from jobs.models import Job
from payments.models import Quotation


@role_required('admin')
def job_summary_report(request):

    jobs = Job.objects.select_related(
        'customer',
        'handyman'
    ).all()

    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    errors = []
    start = None
    end = None

    valid_statuses = dict(Job.STATUS_CHOICES)

    # Validate job status
    if status:
        if status in valid_statuses:
            jobs = jobs.filter(status=status)
        else:
            errors.append('Invalid job status selected.')

    # Validate start date
    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            errors.append('Invalid start date.')

    # Validate end date
    if end_date:
        try:
            end = date.fromisoformat(end_date)
        except ValueError:
            errors.append('Invalid end date.')

    # Check date range
    if start and end and start > end:
        errors.append(
            'Start date cannot be later than end date.'
        )

    # Apply valid filters
    if not errors:
        if start:
            jobs = jobs.filter(
                created_at__date__gte=start
            )

        if end:
            jobs = jobs.filter(
                created_at__date__lte=end
            )

    # Do not show misleading results
    if errors:
        jobs = jobs.none()

    stats = jobs.aggregate(
        total_jobs=Count('id'),
        assigned_jobs=Count(
            'id', filter=Q(status=Job.ASSIGNED)
        ),
        in_progress_jobs=Count(
            'id', filter=Q(status=Job.IN_PROGRESS)
        ),
        completed_jobs=Count(
            'id', filter=Q(status=Job.COMPLETED)
        ),
        cancelled_jobs=Count(
            'id', filter=Q(status=Job.CANCELLED)
        ),
    )

    # FR-A-12.3: the accepted quotation amount and the payment status of each job,
    # taken from the accepted quotations of the job's service request (labour + material).
    jobs = list(jobs.select_related('service_request').prefetch_related(Prefetch(
        'service_request__quotations',
        queryset=Quotation.objects.filter(status=Quotation.ACCEPTED).select_related('payment'),
        to_attr='accepted_quotations',
    )))
    for job in jobs:
        quotes = job.service_request.accepted_quotations if job.service_request else []
        paid = [q for q in quotes if q.is_paid]
        job.quotation_amount = sum(q.total_amount for q in quotes) if quotes else None
        job.payment_state = ('none' if not quotes else 'paid' if len(paid) == len(quotes)
                             else 'partial' if paid else 'unpaid')

    context = {
        'report_title': 'Job Summary Report',
        'jobs': jobs,
        'status_choices': Job.STATUS_CHOICES,
        'selected_status': status,
        'selected_status_label': valid_statuses.get(
            status, 'All statuses'
        ),
        'start_date': start_date,
        'end_date': end_date,
        'errors': errors,
        'filters_valid': not errors,
        **stats,
    }

    return render(
        request,
        'reports/job_summary.html',
        context
    )