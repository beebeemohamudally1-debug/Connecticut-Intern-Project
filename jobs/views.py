from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CompletionForm, EvidenceForm, FlagForm, ProgressReportForm
from .models import Job, ProgressReport, TimeLog, WorkEvidence
from .permissions import base_template_for, get_role, role_required
from .signals import job_completed

ALL_ROLES = ('admin', 'handyman', 'customer')


def jobs_for(user):
    """Jobs the user may see: admin all, handyman/customer only their own."""
    qs = Job.objects.select_related('customer', 'handyman')
    role = get_role(user)
    if role == 'admin':
        return qs
    if role == 'handyman':
        return qs.filter(handyman=user)
    return qs.filter(customer=user)


@role_required(*ALL_ROLES)
def job_list(request):
    role = get_role(request.user)
    jobs = jobs_for(request.user)
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    handyman = request.GET.get('handyman', '')
    if q:
        jobs = jobs.filter(
            Q(reference__icontains=q) | Q(service_name__icontains=q) |
            Q(customer__first_name__icontains=q) | Q(customer__last_name__icontains=q) |
            Q(handyman__first_name__icontains=q) | Q(handyman__last_name__icontains=q))
    if status in dict(Job.STATUS_CHOICES):
        jobs = jobs.filter(status=status)
    if role == 'admin' and handyman.isdigit():
        jobs = jobs.filter(handyman_id=int(handyman))
    jobs = list(jobs)
    if request.GET.get('delayed'):
        jobs = [j for j in jobs if j.is_delayed]
    if request.GET.get('flagged') and role == 'admin':
        jobs = [j for j in jobs if j.is_flagged]
    context = {
        'base_template': base_template_for(request.user), 'role': role, 'jobs': jobs,
        'status_choices': Job.STATUS_CHOICES, 'f': request.GET,
        'handymen': get_user_model().objects.filter(role='handyman') if role == 'admin' else [],
    }
    return render(request, 'jobs/job_list.html', context)


@role_required(*ALL_ROLES)
def job_detail(request, pk):
    job = get_object_or_404(jobs_for(request.user), pk=pk)
    role = get_role(request.user)
    context = {
        'base_template': base_template_for(request.user), 'role': role, 'job': job,
        'time_logs': job.time_logs.all(), 'reports': job.reports.all(),
        'evidence': job.evidence.select_related('uploaded_by'),
        'open_log': job.time_logs.filter(clocked_out_at__isnull=True).first(),
        'complaints': job.complaints.all() if role == 'admin' else [],
    }
    if role == 'handyman' and job.is_open:
        today = job.reports.filter(report_date=timezone.localdate()).first()
        context['report_form'] = ProgressReportForm(instance=today)
        context['evidence_form'] = EvidenceForm()
        context['complete_form'] = CompletionForm()
    if role == 'admin':
        context['flag_form'] = FlagForm()
    return render(request, 'jobs/job_detail.html', context)


def _own_job(request, pk):
    """Job of the logged-in handyman (404 for anyone else's)."""
    return get_object_or_404(Job, pk=pk, handyman=request.user)


@require_POST
@role_required('handyman')
def clock_in(request, pk):
    job = _own_job(request, pk)
    if not job.is_open:
        messages.error(request, 'This job is no longer open.')
    elif job.time_logs.filter(clocked_out_at__isnull=True).exists():
        messages.error(request, 'You are already clocked in on this job.')
    else:
        with transaction.atomic():
            TimeLog.objects.create(job=job, arrived_at=timezone.now())
            if job.status == Job.ASSIGNED:
                job.status = Job.IN_PROGRESS
                job.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Arrival time recorded.')
    return redirect('jobs:detail', pk=pk)


@require_POST
@role_required('handyman')
def clock_out(request, pk):
    job = _own_job(request, pk)
    log = job.time_logs.filter(clocked_out_at__isnull=True).first()
    if not log:
        messages.error(request, 'You are not clocked in on this job.')
    else:
        log.clocked_out_at = timezone.now()
        log.save(update_fields=['clocked_out_at'])
        messages.success(request, 'Clock-out time recorded.')
    return redirect('jobs:detail', pk=pk)


@require_POST
@role_required('handyman')
def submit_report(request, pk):
    job = _own_job(request, pk)
    if not job.is_open:
        messages.error(request, 'This job is no longer open.')
        return redirect('jobs:detail', pk=pk)
    today = job.reports.filter(report_date=timezone.localdate()).first()
    form = ProgressReportForm(request.POST, instance=today)
    if form.is_valid():
        report = form.save(commit=False)
        report.job, report.author = job, request.user
        report.report_date = timezone.localdate()
        report.save()
        messages.success(request, "Today's work report saved.")
    else:
        messages.error(request, 'Report not saved: ' + '; '.join(
            e for errs in form.errors.values() for e in errs))
    return redirect('jobs:detail', pk=pk)


@require_POST
@role_required('handyman')
def upload_evidence(request, pk):
    job = _own_job(request, pk)
    form = EvidenceForm(request.POST, request.FILES)
    if form.is_valid() and job.is_open:
        ev = form.save(commit=False)
        ev.job, ev.uploaded_by = job, request.user
        ev.save()
        messages.success(request, 'Photo uploaded.')
    else:
        messages.error(request, 'Photo not saved: ' + '; '.join(
            e for errs in form.errors.values() for e in errs) if form.errors
            else 'This job is no longer open.')
    return redirect('jobs:detail', pk=pk)


@require_POST
@role_required('handyman')
def complete_job(request, pk):
    job = _own_job(request, pk)
    if job.status != Job.IN_PROGRESS:
        messages.error(request, 'Only a job in progress can be completed. Clock in first.')
        return redirect('jobs:detail', pk=pk)
    form = CompletionForm(request.POST, instance=job)
    if not form.is_valid():
        messages.error(request, '; '.join(e for errs in form.errors.values() for e in errs))
        return redirect('jobs:detail', pk=pk)
    with transaction.atomic():
        job = form.save(commit=False)
        job.status = Job.COMPLETED
        job.completed_at = timezone.now()
        job.save()
        job.time_logs.filter(clocked_out_at__isnull=True).update(clocked_out_at=timezone.now())
    job_completed.send(sender=Job, job=job)
    messages.success(request, 'Job submitted as completed. The administrator has been informed.')
    return redirect('jobs:detail', pk=pk)


@require_POST
@role_required('handyman')
def payout_stage(request, pk, stage):
    """Waiting for payout -> Finished work (FR-H-6.2, FR-H-6.4)."""
    job = _own_job(request, pk)
    if job.status != Job.COMPLETED:
        messages.error(request, 'The job must be completed first.')
    elif stage == 'waiting' and job.payout_stage == Job.PAYOUT_NONE:
        job.payout_stage = Job.PAYOUT_WAITING
        job.save(update_fields=['payout_stage', 'updated_at'])
        messages.success(request, 'Job marked as waiting for payout.')
    elif stage == 'finished' and job.payout_stage == Job.PAYOUT_WAITING:
        job.payout_stage = Job.PAYOUT_FINISHED
        job.save(update_fields=['payout_stage', 'updated_at'])
        messages.success(request, 'Job marked as finished work.')
    else:
        messages.error(request, 'That step is not available now.')
    return redirect('jobs:detail', pk=pk)


def _back(request, pk):
    """Go back to the page the form came from (`next`), if it is on this site; else the job page."""
    nxt = request.POST.get('next', '')
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(nxt)
    return redirect('jobs:detail', pk=pk)


@require_POST
@role_required('admin')
def flag_job(request, pk):
    """Flag, or clear the flag on, a suspicious submission (FR-A-6.6)."""
    job = get_object_or_404(Job, pk=pk)
    if job.is_flagged:
        job.is_flagged, job.flag_reason = False, ''
        job.flagged_by, job.flagged_at = None, None
        messages.success(request, 'Flag removed.')
    else:
        form = FlagForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Give a reason to flag this job.')
            return _back(request, pk)
        job.is_flagged = True
        job.flag_reason = form.cleaned_data['reason']
        job.flagged_by, job.flagged_at = request.user, timezone.now()
        messages.success(request, 'Job flagged.')
    job.save()
    return _back(request, pk)


@role_required(*ALL_ROLES)
def evidence_file(request, pk):
    """Serve a work photo only to people allowed to see the job."""
    ev = get_object_or_404(WorkEvidence.objects.filter(job__in=jobs_for(request.user)), pk=pk)
    return FileResponse(ev.image.open('rb'))
