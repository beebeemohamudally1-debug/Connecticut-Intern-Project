import os
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils import timezone

from accounts.models import HandymanProfile
from bookings.models import HandymanProfileRequest, ServiceRequest
from complaints.models import Complaint, ComplaintMessage
from dashboard.permissions import role_required
from jobs.models import Job
from notifications.models import Notification

User = get_user_model()

@role_required('admin')
def profile(request):
    """Admin Profile: the logged-in administrator. A POST saves the full name and email."""
    u = request.user
    errors = {}
    values = {'full_name': _person_name(u), 'email': u.email}
    if request.method == 'POST':
        full_name = ' '.join(request.POST.get('full_name', '').split())
        email = request.POST.get('email', '').strip().lower()
        values = {'full_name': full_name, 'email': email}
        if not full_name:
            errors['full_name'] = 'Enter your full name.'
        elif len(full_name) > 150:
            errors['full_name'] = 'The full name is too long.'
        if not email:
            errors['email'] = 'Enter your email address.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = 'Enter a valid email address.'
            else:
                if User.objects.filter(email__iexact=email).exclude(pk=u.pk).exists():
                    errors['email'] = 'That email address is already used by another account.'
        if not errors:
            u.first_name, _, u.last_name = full_name.partition(' ')
            u.email = email
            u.save(update_fields=['first_name', 'last_name', 'email'])
            return redirect(reverse('accounts_admin:profile') + '?saved=1')
    admin = {
        'name': _person_name(u),
        'initials': _initials(u),
        'email': u.email,
        'role': 'Administrator',
        'status': 'Active' if u.is_active else 'Inactive',
    }
    return render(request, 'accounts/admin_profile.html', {
        'admin': admin, 'values': values, 'errors': errors,
        'saved': request.GET.get('saved') == '1'})
# ---------- Manage Users (section 3): real accounts.User and accounts.HandymanProfile data ----------
# Not in the backend yet: suspend / reactivate / delete views, registration documents and
# approve / reject, and availability. Those parts of the pages stay as before
# (demo buttons, sample verification page, "Not recorded").

def _profile(u):
    """The handyman's HandymanProfile, or None (customers, or a handyman without one)."""
    try:
        return u.handyman_profile
    except HandymanProfile.DoesNotExist:
        return None


def _account_status(u):
    """Suspended (is_suspended or not is_active) comes first; then a handyman's profile approval."""
    if u.is_suspended or not u.is_active:
        return 'Suspended'
    if u.role == 'handyman':
        profile = _profile(u)
        if profile and profile.status == HandymanProfile.STATUS_PENDING:
            return 'Pending'
        if profile and profile.status == HandymanProfile.STATUS_REJECTED:
            return 'Rejected'
    return 'Active'


def _user_url(u):
    name = 'accounts_admin:handyman_profile' if u.role == 'handyman' else 'accounts_admin:customer_detail'
    return reverse(name, args=[u.pk])

def _action_urls(u):
    """Addresses of the Suspend / Reactivate / Delete actions for the pop-ups."""
    return {
        'suspend_url': reverse('accounts_admin:suspend_user', args=[u.pk]),
        'reactivate_url': reverse('accounts_admin:reactivate_user', args=[u.pk]),
        'delete_url': reverse('accounts_admin:delete_user', args=[u.pk]),
    }

def _local_date(dt):
    return timezone.localtime(dt).strftime('%d %B %Y') if dt else '-'


SEARCH_LIMIT = 6   # results shown per group; the rest is counted


def _match(qs, text, fields):
    """Every word of the search text must be found in one of the fields ("alex smith" finds Alex Smith)."""
    for word in text.split():
        cond = Q()
        for f in fields:
            cond |= Q(**{f + '__icontains': word})
        qs = qs.filter(cond)
    return qs.distinct()


@role_required('admin')
def search(request):
    """Navbar search: users, jobs and service requests matching ?q= (read only)."""
    q = request.GET.get('q', '').strip()
    groups = []
    if q:
        people = _match(User.objects.filter(role__in=['customer', 'handyman']), q,
                        ['username', 'first_name', 'last_name', 'email', 'phone']).order_by('first_name', 'last_name')
        jobs = _match(Job.objects.select_related('customer', 'handyman'), q,
                      ['reference', 'service_name', 'address', 'customer__first_name', 'customer__last_name',
                       'handyman__first_name', 'handyman__last_name']).order_by('-created_at')
        requests_ = _match(ServiceRequest.objects.select_related('customer'), q,
                           ['reference', 'service_category', 'service_address', 'contact_name',
                            'customer__first_name', 'customer__last_name']).order_by('-created_at')
        groups = [
            {'key': 'users', 'title': 'Users', 'count': people.count(), 'rows': [{
                'title': _person_name(u), 'sub': f'{u.get_role_display()} · {u.email or u.username}',
                'tag': _account_status(u), 'tone': 'ok' if u.is_active else 'bad', 'url': _user_url(u),
            } for u in people[:SEARCH_LIMIT]]},
            {'key': 'jobs', 'title': 'Jobs', 'count': jobs.count(), 'rows': [{
                'title': f'{j.reference} · {j.service_name}',
                'sub': f'{_person_name(j.customer)} → {_person_name(j.handyman)}',
                'tag': _job_state(j)[1], 'tone': 'info',
                'url': reverse('accounts_admin:work_progress_job', args=[j.pk]),
            } for j in jobs[:SEARCH_LIMIT]]},
            {'key': 'requests', 'title': 'Service requests', 'count': requests_.count(), 'rows': [{
                'title': f'{r.reference} · {r.service_category or "Service request"}',
                'sub': _person_name(r.customer), 'tag': r.get_status_display(), 'tone': 'info',
                'url': reverse('bookings:admin_request_detail', args=[r.pk]),
            } for r in requests_[:SEARCH_LIMIT]]},
        ]
    page = {'q': q, 'groups': groups, 'total': sum(g['count'] for g in groups), 'limit': SEARCH_LIMIT}
    return render(request, 'accounts/admin_search.html', {'page': page})


@role_required('admin')
def users(request):
    """Manage Users: every customer and handyman, newest first."""
    accounts = (User.objects.filter(role__in=['customer', 'handyman'])
                .select_related('handyman_profile').order_by('-date_joined'))
    rows = [{
        'name': _person_name(u), 'initials': _initials(u), 'role': u.get_role_display(),
        'email': u.email, 'status': _account_status(u), 'url': _user_url(u),
    } for u in accounts]
    stats = {
        'total': len(rows),
        'customers': sum(1 for u in accounts if u.role == 'customer'),
        'handymen': sum(1 for u in accounts if u.role == 'handyman'),
        'pending': sum(1 for r in rows if r['status'] == 'Pending'),   # handymen waiting for approval
    }
    return render(request, 'accounts/admin_users.html', {'page': {'stats': stats, 'users': rows}})


@role_required('admin')
def customer_detail(request, pk):
    """Customer Details: account, contact and service requests (bookings.ServiceRequest)."""
    u = get_object_or_404(User, pk=pk, role='customer')
    reqs = list(ServiceRequest.objects.filter(customer=u).order_by('-created_at'))
    done, cancelled = ServiceRequest.STATUS_COMPLETED, ServiceRequest.STATUS_CANCELLED
    customer = {
                **_action_urls(u),
        'kind': 'customer', 'name': _person_name(u), 'initials': _initials(u),
        'id': f'USR-{u.pk:04d}', 'registered': _local_date(u.date_joined),
        'email': u.email or '-', 'phone': u.phone or '-',
        # The user's address; if empty, the address of the latest service request
        'address': u.address or (reqs[0].service_address if reqs else '-'),
        'status': _account_status(u),
        'counts': {
            'submitted': len(reqs),
            'completed': Job.objects.filter(customer=u, status=Job.COMPLETED).count(),
            'pending': sum(1 for r in reqs if r.status not in (done, cancelled)),
            'cancelled': sum(1 for r in reqs if r.status == cancelled),
        },
        'requests': [{
            'id': r.reference, 'title': r.service_category, 'status': r.get_status_display(),
            'url': reverse('bookings:admin_request_detail', args=[r.pk]),   # Service Request Details
            'state': 'done' if r.status == done else 'cancel' if r.status == cancelled else 'wait',
        } for r in reqs],
    }
    return render(request, 'accounts/admin_customer_detail.html', {'customer': customer})


def _approved_values(u, kind):
    """Current skills or services: the handyman's approved add / modify / remove requests, oldest first."""
    values = []
    for r in (HandymanProfileRequest.objects
              .filter(handyman=u, request_type=kind, status=HandymanProfileRequest.STATUS_APPROVED)
              .order_by('reviewed_at', 'submitted_at')):
        if r.action == HandymanProfileRequest.ACTION_ADD:
            values.append(r.requested_value)
        elif r.action == HandymanProfileRequest.ACTION_MODIFY:
            values = [r.requested_value if v == r.current_value else v for v in values]
        else:
            values = [v for v in values if v != r.current_value]
    return values


@role_required('admin')
def handyman_profile(request, pk):
    """Handyman Profile: account, jobs, and the skills, services and areas of the HandymanProfile."""
    u = get_object_or_404(User.objects.select_related('region'), pk=pk, role='handyman')
    jobs = list(Job.objects.filter(handyman=u))
    latest = jobs[0] if jobs else None          # newest first
    profile = _profile(u)
    if profile:
        skills = [s.name for s in profile.skills.order_by('name')]
        services = [s.name for s in profile.services.order_by('name')]
        areas = ', '.join(a.name for a in profile.service_areas.order_by('name'))
        verified = profile.status == HandymanProfile.STATUS_ACTIVE   # approved by an administrator
    else:
        # No profile yet (older accounts): fall back to the approved profile change requests
        skills = _approved_values(u, HandymanProfileRequest.TYPE_SKILL)
        services = _approved_values(u, HandymanProfileRequest.TYPE_SERVICE)
        areas, verified = '', None
    handyman = {
                'pk': u.pk,
                **_action_urls(u),
        'kind': 'handyman', 'name': _person_name(u), 'initials': _initials(u),
        'id': f'USR-{u.pk:04d}', 'verified': verified,
        'status': _account_status(u), 'email': u.email or '-', 'phone': u.phone or '-',
        'areas': areas or (u.region.name if u.region else 'Not recorded'),
        'availability': 'Not recorded',   # no availability field in the backend yet
        'registered': _local_date(u.date_joined),
        'completed': sum(1 for j in jobs if j.status == Job.COMPLETED),
        'assigned': sum(1 for j in jobs if j.is_open),
        'skills': skills,
        'services': services,
        'reports_url': reverse('accounts_admin:work_progress_reports', args=[latest.pk]) if latest else '',
    }
    return render(request, 'accounts/admin_handyman_profile.html', {'handyman': handyman})

@role_required('admin')
def notifications(request):
    """Display real notifications for the administrator."""

    notifications_list = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    unread_count = notifications_list.filter(
        is_read=False
    ).count()

    return render(
        request,
        'notifications/admin_notifications.html',
        {
            'notifications': notifications_list,
            'unread_count': unread_count,
        }
    )
# ---------- Monitor Work Progress (section 5): real data from the jobs app ----------
# Admin-only views over jobs.Job, TimeLog, ProgressReport and WorkEvidence.
# Flagging posts to the jobs app's own view (jobs:flag) with a `next` field,
# so the admin comes back to the same Work Evidence page.

def _job_state(job):
    """Status for the pill: 'delayed' when an open job is past its due date (job.is_delayed)."""
    if job.is_delayed:
        return 'delayed', 'Delayed'
    return job.status, job.get_status_display()


def _job_percent(job, latest):
    """Latest report's percent complete; a completed job shows 100%."""
    if job.status == Job.COMPLETED:
        return 100
    return latest.percent_complete if latest else 0


def _photos_by_day(job):
    """WorkEvidence belongs to the job, so photos are matched to a report by upload day."""
    days = {}
    for e in job.evidence.all():
        days.setdefault(timezone.localtime(e.uploaded_at).date(), []).append(e)
    return days


def _get_job(pk):
    return get_object_or_404(
        Job.objects.select_related('customer', 'handyman', 'service_request', 'flagged_by')
        .prefetch_related('reports__author', 'time_logs', 'evidence'), pk=pk)


@role_required('admin')
def work_progress(request):
    """Monitor Work Progress - Overview (every job except cancelled ones)."""
    jobs = (Job.objects.exclude(status=Job.CANCELLED)
            .select_related('customer', 'handyman').prefetch_related('reports'))
    rows = []
    for j in jobs:
        status, label = _job_state(j)
        latest = next(iter(j.reports.all()), None)
        rows.append({
            'reference': j.reference, 'service': j.service_name,
            'customer': _person_name(j.customer), 'handyman': _person_name(j.handyman),
            'percent': _job_percent(j, latest), 'due': j.due_date,
            'status': status, 'status_label': label, 'is_flagged': j.is_flagged,
            'url': reverse('accounts_admin:work_progress_job', args=[j.pk]),
        })
    services = sorted({r['service'] for r in rows})
    return render(request, 'jobs/admin_work_progress.html', {'page': {'services': services, 'jobs': rows}})


@role_required('admin')
def job_progress(request, pk):
    """Monitor Work Progress - Job Progress Details."""
    j = _get_job(pk)
    status, label = _job_state(j)
    reports = list(j.reports.all())            # newest first
    latest = reports[0] if reports else None
    logs = sorted(j.time_logs.all(), key=lambda t: t.arrived_at)
    started = logs[0].arrived_at if logs else None
    handyman, customer = _person_name(j.handyman), _person_name(j.customer)

    timeline = [{'kind': 'assigned', 'title': 'Assigned to handyman', 'when': j.created_at,
                 'text': f'{handyman} assigned to the {j.service_name.lower()} job for {customer}.'}]
    if started:
        timeline.append({'kind': 'started', 'title': 'Work started', 'when': started,
                         'text': f'{handyman} arrived on site.'})
    for r in reversed(reports):                # oldest first
        timeline.append({'kind': 'report', 'title': f'Daily report added · {r.percent_complete}%',
                         'when': r.updated_at, 'text': r.details})
    overdue = ''
    if j.is_delayed:
        days = (timezone.localdate() - j.due_date).days
        overdue = f'{days} day{"s" if days != 1 else ""} overdue'
        missed = timezone.make_aware(datetime.combine(j.due_date + timedelta(days=1), time.min))
        timeline.append({'kind': 'delay', 'title': 'Due date missed', 'when': missed,
                         'text': f'Expected completion was {j.due_date:%d %b %Y}. The job is still open.'})
    if j.completed_at:
        timeline.append({'kind': 'started', 'title': 'Job completed', 'when': j.completed_at,
                         'text': j.completion_notes or f'{handyman} marked the job as completed.'})
    if j.is_flagged and j.flagged_at:
        timeline.append({'kind': 'delay', 'title': 'Flagged for review', 'when': j.flagged_at,
                         'text': j.flag_reason})
    timeline.sort(key=lambda e: e['when'])
    # Only 4 events fit on one screen: the assignment and the latest 3 (all reports are on Daily Work Reports).
    if len(timeline) > 4:
        timeline = timeline[:1] + timeline[-3:]

    job = {
        'reference': j.reference, 'title': j.description.splitlines()[0][:80] if j.description else j.service_name,
        'handyman': handyman, 'customer': customer, 'started': started, 'due': j.due_date,
        'service': j.service_name,
        'request_ref': j.service_request.reference if j.service_request else '',
        'scheduled': j.scheduled_start,
        'status': status, 'status_label': label, 'percent': _job_percent(j, latest),
        'overdue': overdue, 'latest_note': latest.details if latest else '',
        'last_report': latest.updated_at if latest else None,
        'is_flagged': j.is_flagged, 'flag_reason': j.flag_reason, 'timeline': timeline,
        'reports_url': reverse('accounts_admin:work_progress_reports', args=[j.pk]),
        # ?from=job so the Evidence page's back link returns here
        'evidence_url': reverse('accounts_admin:work_progress_evidence', args=[j.pk]) + '?from=job',
    }
    return render(request, 'jobs/admin_job_progress.html', {'job': job})


@role_required('admin')
def daily_reports(request, pk):
    """Monitor Work Progress - Daily Work Reports for one job (newest first)."""
    j = _get_job(pk)
    photos = _photos_by_day(j)
    reports = [{
        'report_date': r.report_date, 'updated_at': r.updated_at, 'handyman': _person_name(r.author),
        'details': r.details, 'percent': r.percent_complete, 'photos': len(photos.get(r.report_date, [])),
        'url': reverse('accounts_admin:work_progress_report_evidence', args=[j.pk, r.pk]),
    } for r in j.reports.all()]
    page = {
        'reference': j.reference, 'service': j.service_name, 'customer': _person_name(j.customer),
        'job_url': reverse('accounts_admin:work_progress_job', args=[j.pk]),
        'handymen': sorted({r['handyman'] for r in reports}), 'reports': reports,
    }
    return render(request, 'jobs/admin_daily_reports.html', {'page': page})


@role_required('admin')
def work_evidence(request, pk, report_pk=None):
    """Monitor Work Progress - Work Evidence & Completion Notes.

    With a report: the photos uploaded on that report's day. Without one (the
    View Evidence button): the latest report, or every photo if there is no report yet.
    """
    j = _get_job(pk)
    reports = list(j.reports.all())
    if report_pk is not None:
        report = next((r for r in reports if r.pk == report_pk), None)
        if report is None:
            raise Http404('No such report for this job.')
    else:
        report = reports[0] if reports else None
    photos = _photos_by_day(j).get(report.report_date, []) if report else list(j.evidence.all())
    status, label = _job_state(j)
    here = request.get_full_path()
    from_job = request.GET.get('from') == 'job'
    page = {
        'reference': j.reference,
        'title': j.description.splitlines()[0][:80] if j.description else j.service_name,
        'reports_url': reverse('accounts_admin:work_progress_reports', args=[j.pk]),
        'job_url': reverse('accounts_admin:work_progress_job', args=[j.pk]),
        'back_url': reverse('accounts_admin:work_progress_job' if from_job else 'accounts_admin:work_progress_reports', args=[j.pk]),
        'back_label': 'Job Progress Details' if from_job else 'Daily Work Reports',
        'report_date': report.report_date if report else None,
        'updated_at': report.updated_at if report else None,
        'handyman': _person_name(report.author if report else j.handyman),
        'status': status, 'status_label': label,
        'photos': [{'caption': e.caption, 'filename': os.path.basename(e.image.name),
                    'url': reverse('jobs:evidence_file', args=[e.pk])} for e in photos],
        'notes': j.completion_notes or (report.details if report else ''),
        'notes_title': 'Completion notes' if j.completion_notes or not report else 'Report notes',
        'is_flagged': j.is_flagged, 'flag_reason': j.flag_reason,
        'flag_url': reverse('jobs:flag', args=[j.pk]), 'next_url': here,
    }
    return render(request, 'jobs/admin_work_evidence.html', {'page': page})

# ---------- Complaints (section 12): real data from the complaints app ----------
# The pages post to the complaints app's own views (complaints:enquiry and
# complaints:resolution) with a `next` field, so the admin comes back to the same page.

def _person_name(user):
    return (user.get_full_name() or user.username) if user else 'Unknown'


def _initials(user):
    if not user:
        return '?'
    parts = (user.get_full_name() or user.username).split()
    return ''.join(p[0] for p in parts[:2]).upper()


def _complaint_people(c):
    """The customer and the handyman on a complaint (either one may have filed it)."""
    people = [u for u in (c.submitted_by, c.against) if u]
    customer = next((u for u in people if u.role == 'customer'), None)
    handyman = next((u for u in people if u.role == 'handyman'), None)
    return customer, handyman


def _thread(c, person):
    """Messages between the administrator and one person: enquiries to them and their replies."""
    if not person:
        return []
    return [m for m in c.messages.all() if m.recipient_id == person.pk or m.author_id == person.pk]


def _case_page(c):
    """Everything the case, chat and resolve pages need about one complaint."""
    customer, handyman = _complaint_people(c)
    customer_msgs, handyman_msgs = _thread(c, customer), _thread(c, handyman)
    labels = dict(Complaint.STATUS_CHOICES)
    activity = [{'title': log.note or f'Moved to {labels.get(log.to_status, log.to_status).lower()}',
                 'at': log.created_at, 'done': True} for log in c.log.all()]
    evidence = []
    for e in c.evidence.all():
        try:
            size = filesizeformat(e.file.size)
        except (OSError, ValueError):
            size = ''
        evidence.append({'name': os.path.basename(e.file.name), 'size': size,
                         'url': reverse('complaints:evidence_file', args=[e.pk])})
    return {
        'pk': c.pk, 'reference': c.reference, 'subject': c.subject, 'description': c.description,
        'status': c.status, 'status_label': c.get_status_display(), 'is_resolved': c.is_resolved,
        'created_at': c.created_at, 'job': c.job.reference,
        'filed_by': _person_name(c.submitted_by), 'against': _person_name(c.against),
        'customer_name': _person_name(customer), 'handyman_name': _person_name(handyman),
        'customer': customer, 'handyman': handyman, 'evidence': evidence,
        'customer_msgs': len(customer_msgs), 'handyman_msgs': len(handyman_msgs),
        'customer_thread': customer_msgs, 'handyman_thread': handyman_msgs,
        'activity': activity,
        'outcome': c.outcome, 'resolved_by': _person_name(c.resolved_by), 'resolved_at': c.resolved_at,
        'queue_url': reverse('accounts_admin:complaints'),
        'case_url': reverse('accounts_admin:complaint_case', args=[c.pk]),
        'customer_url': reverse('accounts_admin:complaint_customer', args=[c.pk]),
        'handyman_url': reverse('accounts_admin:complaint_handyman', args=[c.pk]),
        'resolve_url': reverse('accounts_admin:complaint_resolve', args=[c.pk]),
        'status_url': reverse('complaints:resolution', args=[c.pk]),
        'enquiry_url': reverse('complaints:enquiry', args=[c.pk]),
        'resolution_url': reverse('complaints:resolution', args=[c.pk]),
    }


def _get_complaint(pk):
    return get_object_or_404(
        Complaint.objects.select_related('submitted_by', 'against', 'job', 'resolved_by')
        .prefetch_related('messages__author', 'log', 'evidence'), pk=pk)


@role_required('admin')
def complaint_queue(request):
    """Complaints - Complaint Queue (all complaints, newest first)."""
    rows = [{
        'reference': c.reference, 'subject': c.subject, 'filed_by': _person_name(c.submitted_by),
        'role': c.submitted_by.role, 'role_label': c.submitted_by.get_role_display(),
        'job': c.job.reference, 'created_at': c.created_at,
        'status': c.status, 'status_label': c.get_status_display(),
        'url': reverse('accounts_admin:complaint_case', args=[c.pk]),
    } for c in Complaint.objects.select_related('submitted_by', 'job')]
    stats = {'total': len(rows)}
    for key in (Complaint.PENDING, Complaint.IN_PROGRESS, Complaint.RESOLVED):
        stats[key] = sum(1 for r in rows if r['status'] == key)
    return render(request, 'complaints/admin_complaint_queue.html', {'page': {'stats': stats, 'complaints': rows}})


@role_required('admin')
def complaint_case(request, pk):
    """Complaints - Case Overview (also shows a resolved case)."""
    return render(request, 'complaints/admin_complaint_case.html', {'page': _case_page(_get_complaint(pk))})


@role_required('admin')
def complaint_conversation(request, pk, who):
    """Complaints - private conversation with the customer or the handyman."""
    page = _case_page(_get_complaint(pk))
    person = page[who]
    if person is None:
        raise Http404('This complaint has no ' + who + '.')
    other = 'handyman' if who == 'customer' else 'customer'
    page.update({
        'who': who.capitalize(), 'other_label': other.capitalize(), 'other_url': page[other + '_url'],
        'person': {'name': _person_name(person), 'first_name': person.first_name or person.username,
                   'initials': _initials(person), 'email': person.email},
        'recipient_id': person.pk,
        'messages': [{'author': _person_name(m.author), 'from_admin': m.kind == ComplaintMessage.ENQUIRY,
                      'at': m.created_at, 'body': m.body} for m in page[who + '_thread']],
        'next_url': page[who + '_url'],
    })
    return render(request, 'complaints/admin_complaint_conversation.html', {'page': page})


@role_required('admin')
def complaint_resolve(request, pk):
    """Complaints - Resolve case (a resolved case goes back to its overview)."""
    c = _get_complaint(pk)
    if c.is_resolved:
        return redirect('accounts_admin:complaint_case', pk=c.pk)
    page = _case_page(c)
    customer, handyman = page['customer'], page['handyman']
    page['checks'] = {
        'customer_replied': any(m.author_id == getattr(customer, 'pk', None) for m in page['customer_thread']),
        'handyman_replied': any(m.author_id == getattr(handyman, 'pk', None) for m in page['handyman_thread']),
        'has_evidence': bool(page['evidence']),
    }
    return render(request, 'complaints/admin_complaint_resolve.html', {'page': page})