import os
from datetime import datetime, time, timedelta

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils import timezone

from complaints.models import Complaint, ComplaintMessage
from dashboard.permissions import role_required
from jobs.models import Job
from notifications.models import Notification

@role_required('admin')
def profile(request):
    """Admin Profile: the logged-in administrator.

    Saving is not connected yet: the accounts app has no profile update view
    (the form keeps data-demo until one exists).
    """
    u = request.user
    admin = {
        'name': _person_name(u),
        'initials': _initials(u),
        'email': u.email,
        'role': 'Administrator',
        'status': 'Active' if u.is_active else 'Inactive',
    }
    return render(request, 'accounts/admin_profile.html', {'admin': admin})

# Sample data for Manage Users until the real accounts are connected
USERS_PAGE = {
    'stats': {'total': '1,284', 'customers': 842, 'handymen': 442, 'pending': 18},
    'users': [
        {'name': 'Sarah Thompson', 'initials': 'ST', 'role': 'Customer', 'email': 'sarah.thompson@email.com', 'status': 'Active', 'url': '/admin-portal/users/customer/'},
        {'name': 'Marcus Reed', 'initials': 'MR', 'role': 'Handyman', 'email': 'marcus.reed@email.com', 'status': 'Active', 'url': '/admin-portal/users/handyman/'},
        {'name': 'Daniel Brooks', 'initials': 'DB', 'role': 'Customer', 'email': 'daniel.brooks@email.com', 'status': 'Suspended', 'url': '/admin-portal/users/customer/suspended/'},
        {'name': 'Amir Patel', 'initials': 'AP', 'role': 'Handyman', 'email': 'amir.patel@email.com', 'status': 'Pending', 'url': '/admin-portal/users/handyman/verify/'},
        {'name': 'Emma Wilson', 'initials': 'EW', 'role': 'Customer', 'email': 'emma.wilson@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Priya Nair', 'initials': 'PN', 'role': 'Customer', 'email': 'priya.nair@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Kevin Dubois', 'initials': 'KD', 'role': 'Handyman', 'email': 'kevin.dubois@email.com', 'status': 'Pending', 'url': '#'},
        {'name': 'Aisha Rahman', 'initials': 'AR', 'role': 'Customer', 'email': 'aisha.rahman@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Jean Laval', 'initials': 'JL', 'role': 'Handyman', 'email': 'jean.laval@email.com', 'status': 'Suspended', 'url': '/admin-portal/users/handyman/suspended/'},
        {'name': 'Nadia Bhuruth', 'initials': 'NB', 'role': 'Customer', 'email': 'nadia.bhuruth@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Ravi Gopaul', 'initials': 'RG', 'role': 'Handyman', 'email': 'ravi.gopaul@email.com', 'status': 'Active', 'url': '#'},
    ],
}


def users(request):
    """Manage Users."""
    return render(request, 'accounts/admin_users.html', {'page': USERS_PAGE})



# Sample data for the Customer Details page
CUSTOMER = {
    'kind': 'customer',
    'name': 'Sarah Thompson',
    'initials': 'ST',
    'id': 'USR-0042',
    'registered': '12 March 2026',
    'email': 'sarah.thompson@email.com',
    'phone': '+230 5 987 6543',
    'address': 'Quatre Bornes, Mauritius',
    'status': 'Active',
    'counts': {'submitted': '08', 'completed': '05', 'pending': '02', 'cancelled': '01'},
    'requests': [
        {'id': 'REQ-2086', 'title': 'Bathroom plumbing', 'status': 'Pending'},
        {'id': 'REQ-2073', 'title': 'Electrical repair', 'status': 'Completed'},
        {'id': 'REQ-2044', 'title': 'Tap replacement', 'status': 'Completed'},
        {'id': 'REQ-2031', 'title': 'Door lock repair', 'status': 'Completed'},
        {'id': 'REQ-2019', 'title': 'Ceiling fan installation', 'status': 'Cancelled'},
        {'id': 'REQ-1998', 'title': 'Kitchen sink unblocking', 'status': 'Completed'},
        {'id': 'REQ-1974', 'title': 'Wall painting', 'status': 'Pending'},
        {'id': 'REQ-1952', 'title': 'Light fitting', 'status': 'Completed'},
    ],
}

# Sample data for the Handyman Profile page
HANDYMAN = {
    'kind': 'handyman',
    'name': 'Marcus Reed',
    'initials': 'MR',
    'id': 'USR-0874',
    'verified': True,
    'status': 'Active',
    'email': 'marcus.reed@email.com',
    'phone': '+230 5 731 1145',
    'areas': 'Port Louis · Pamplemousses',
    'availability': 'Mon–Sat · 08:00–17:00',
    'registered': '13 May 2026',
    'completed': '48',
    'assigned': '03',
    'skills': ['Bathroom plumbing', 'Water heater repair', 'Pipe installation'],
    'services': ['Bathroom plumbing', 'Pipe leak repair', 'Water heater installation', 'General plumbing maintenance'],
}

# Sample data for a suspended customer (the page shows Reactivate instead of Suspend)
SUSPENDED_CUSTOMER = {
    'kind': 'customer',
    'name': 'Daniel Brooks',
    'initials': 'DB',
    'id': 'USR-0057',
    'registered': '04 February 2026',
    'email': 'daniel.brooks@email.com',
    'phone': '+230 5 412 7788',
    'address': 'Curepipe, Mauritius',
    'status': 'Suspended',
    'counts': {'submitted': '03', 'completed': '01', 'pending': '01', 'cancelled': '01'},
    'requests': [
        {'id': 'REQ-2062', 'title': 'Door lock repair', 'status': 'Pending'},
        {'id': 'REQ-2011', 'title': 'Ceiling fan installation', 'status': 'Cancelled'},
        {'id': 'REQ-1969', 'title': 'Tap replacement', 'status': 'Completed'},
    ],
}

# Sample data for a suspended handyman
SUSPENDED_HANDYMAN = {
    'kind': 'handyman',
    'name': 'Jean Laval',
    'initials': 'JL',
    'id': 'USR-0912',
    'verified': True,
    'status': 'Suspended',
    'email': 'jean.laval@email.com',
    'phone': '+230 5 644 2091',
    'areas': 'Curepipe · Quatre Bornes',
    'availability': 'Mon–Fri · 09:00–16:00',
    'registered': '21 June 2026',
    'completed': '12',
    'assigned': '00',
    'skills': ['Electrical repair', 'Light fitting'],
    'services': ['Electrical repair', 'Light fitting installation'],
}

# Sample data for the Registration Verification page
APPLICANT = {
    'id': 'HND-0184',
    'name': 'Amir Patel',
    'email': 'amir.patel@email.com',
    'submitted': '03 Nov 2026',
    'status': 'Pending',
    'documents': [
        {'title': 'National Identity Card', 'file': 'identity-card.pdf', 'action': 'View document'},
        {'title': 'Trade qualification', 'file': 'plumbing-certificate.pdf', 'action': 'View document'},
        {'title': 'Proof of address', 'file': 'proof-of-address.pdf', 'action': 'View document'},
        {'title': 'Profile photograph', 'file': 'handyman-photo.jpg', 'action': 'View image'},
        {'title': 'Police character certificate', 'file': 'police-certificate.pdf', 'action': 'View document'},
        {'title': 'Reference letter', 'file': 'reference-letter.pdf', 'action': 'View document'},
    ],
}


# The same page for a handyman who was already approved (opened from the profile)
APPROVED_APPLICANT = {
    'id': 'USR-0874',
    'name': 'Marcus Reed',
    'email': 'marcus.reed@email.com',
    'submitted': '10 May 2026',
    'status': 'Approved',
    'decided': '13 May 2026',
    'notes': 'All documents checked and valid.',
    'documents': APPLICANT['documents'],
}


def customer_detail(request):
    """Customer Details."""
    return render(request, 'accounts/admin_customer_detail.html', {'customer': CUSTOMER})


def handyman_profile(request):
    """Handyman Profile."""
    return render(request, 'accounts/admin_handyman_profile.html', {'handyman': HANDYMAN})


def handyman_verify(request):
    """Handyman Registration Verification."""
    return render(request, 'accounts/admin_handyman_verify.html', {'applicant': APPLICANT})


def handyman_documents(request):
    """Registration documents of an already approved handyman (read only)."""
    return render(request, 'accounts/admin_handyman_verify.html', {'applicant': APPROVED_APPLICANT})


def suspended_customer(request):
    """Customer Details for a suspended account."""
    return render(request, 'accounts/admin_customer_detail.html', {'customer': SUSPENDED_CUSTOMER})


def suspended_handyman(request):
    """Handyman Profile for a suspended account."""
    return render(request, 'accounts/admin_handyman_profile.html', {'handyman': SUSPENDED_HANDYMAN})

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