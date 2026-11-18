import os
from datetime import datetime

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import filesizeformat
from django.urls import reverse

from complaints.models import Complaint, ComplaintMessage
from dashboard.permissions import role_required
from notifications.models import Notification

# Sample data until the real administrator is connected
ADMIN_PROFILE = {
    'name': 'Admin User',
    'initials': 'AU',
    'email': 'admin@handyconnect.example',
    'role': 'Administrator',
    'status': 'Active',
}

def profile(request):
    """Admin Profile."""
    return render(request, 'accounts/admin_profile.html', {'admin': ADMIN_PROFILE})

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
# Sample data for Monitor Work Progress until the real jobs are connected
from datetime import date

WORK_PROGRESS = {
    'services': ['Appliance Repair', 'Carpentry', 'Electrical', 'Painting', 'Plumbing'],
    'jobs': [
        {'reference': 'JOB-1042', 'service': 'Plumbing', 'customer': 'Emma Wilson', 'handyman': 'Marcus Reed', 'percent': 65, 'due': date(2026, 10, 28), 'status': 'delayed', 'status_label': 'Delayed', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1051', 'service': 'Electrical', 'customer': 'Daniel Brooks', 'handyman': 'Sofia Martinez', 'percent': 40, 'due': date(2026, 10, 30), 'status': 'in_progress', 'status_label': 'In Progress', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1046', 'service': 'Painting', 'customer': 'Amy Lee', 'handyman': 'James Carter', 'percent': 100, 'due': date(2026, 10, 28), 'status': 'completed', 'status_label': 'Completed', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1053', 'service': 'Carpentry', 'customer': 'Rachel Kim', 'handyman': 'Ethan Taylor', 'percent': 0, 'due': date(2026, 11, 2), 'status': 'assigned', 'status_label': 'Assigned', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1049', 'service': 'Appliance Repair', 'customer': 'David Park', 'handyman': 'Noah Williams', 'percent': 80, 'due': date(2026, 10, 30), 'status': 'in_progress', 'status_label': 'In Progress', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1054', 'service': 'Plumbing', 'customer': 'Sarah Patel', 'handyman': 'Marcus Reed', 'percent': 0, 'due': date(2026, 11, 3), 'status': 'assigned', 'status_label': 'Assigned', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1055', 'service': 'Electrical', 'customer': 'Priya Nair', 'handyman': 'Sofia Martinez', 'percent': 55, 'due': date(2026, 11, 4), 'status': 'in_progress', 'status_label': 'In Progress', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1047', 'service': 'Painting', 'customer': 'Kevin Dubois', 'handyman': 'James Carter', 'percent': 100, 'due': date(2026, 10, 27), 'status': 'completed', 'status_label': 'Completed', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1048', 'service': 'Carpentry', 'customer': 'Aisha Rahman', 'handyman': 'Ethan Taylor', 'percent': 30, 'due': date(2026, 10, 29), 'status': 'delayed', 'status_label': 'Delayed', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1056', 'service': 'Appliance Repair', 'customer': 'Nadia Bhuruth', 'handyman': 'Noah Williams', 'percent': 0, 'due': date(2026, 11, 5), 'status': 'assigned', 'status_label': 'Assigned', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1050', 'service': 'Plumbing', 'customer': 'Jean Laval', 'handyman': 'Marcus Reed', 'percent': 90, 'due': date(2026, 11, 1), 'status': 'in_progress', 'status_label': 'In Progress', 'url': '/admin-portal/work-progress/job/'},
        {'reference': 'JOB-1052', 'service': 'Electrical', 'customer': 'Ravi Gopaul', 'handyman': 'Sofia Martinez', 'percent': 100, 'due': date(2026, 10, 31), 'status': 'completed', 'status_label': 'Completed', 'url': '/admin-portal/work-progress/job/'},
    ],
}


def work_progress(request):
    """Monitor Work Progress - Overview."""
    return render(request, 'jobs/admin_work_progress.html', {'page': WORK_PROGRESS})

# Sample data for Job Progress Details until the real job is connected
JOB_PROGRESS = {
    'reference': 'JOB-1042',
    'title': 'Kitchen pipe repair and replacement',
    'handyman': 'Marcus Reed',
    'customer': 'Emma Wilson',
    'started': datetime(2026, 10, 27, 9, 0),
    'due': date(2026, 10, 28),
    'service': 'Plumbing',
    'request_ref': 'REQ-3128',
    'scheduled': date(2026, 10, 27),
    'status': 'delayed',
    'status_label': 'Delayed',
    'percent': 65,
    'overdue': '1 day overdue',
    'latest_note': 'Awaiting replacement fitting. Final pressure test is still pending.',
    'last_report': datetime(2026, 10, 29, 16, 45),
    'reports_url': '/admin-portal/work-progress/reports/',
    'evidence_url': '/admin-portal/work-progress/evidence/',
    'timeline': [
        {'kind': 'assigned', 'title': 'Assigned to handyman', 'when': datetime(2026, 10, 26, 10, 30), 'text': 'Marcus Reed assigned to the plumbing repair for Emma Wilson.'},
        {'kind': 'started', 'title': 'Work Started', 'when': datetime(2026, 10, 27, 9, 0), 'text': 'Site inspection completed; damaged kitchen pipework removed.'},
        {'kind': 'report', 'title': 'Daily Report added', 'when': datetime(2026, 10, 28, 16, 20), 'text': 'Replacement pipework installed. Progress updated from 35% to 65%.'},
        {'kind': 'delay', 'title': 'Delay reported · Daily Report added', 'when': datetime(2026, 10, 29, 16, 45), 'text': 'Final fitting is unavailable. Expected completion missed by 1 day.'},
    ],
}


def job_progress(request):
    """Monitor Work Progress - Job Progress Details."""
    return render(request, 'jobs/admin_job_progress.html', {'job': JOB_PROGRESS})

# Sample data for Daily Work Reports until the real reports are connected
DAILY_REPORTS = {
    'reference': 'JOB-1042',
    'service': 'Plumbing',
    'customer': 'Emma Wilson',
    'job_url': '/admin-portal/work-progress/job/',
    'handymen': ['Marcus Reed'],
    'reports': [
        {'report_date': date(2026, 10, 29), 'updated_at': datetime(2026, 10, 29, 16, 45), 'handyman': 'Marcus Reed', 'percent': 65, 'photos': 3, 'url': '/admin-portal/work-progress/evidence/',
         'details': 'Main pipework fitted. Waiting for a replacement elbow fitting before the final pressure test and handover.'},
        {'report_date': date(2026, 10, 28), 'updated_at': datetime(2026, 10, 28, 16, 20), 'handyman': 'Marcus Reed', 'percent': 65, 'photos': 4, 'url': '/admin-portal/work-progress/evidence/',
         'details': 'Replacement supply pipes installed and joints secured. Initial leak checks completed; final fitting still required.'},
        {'report_date': date(2026, 10, 27), 'updated_at': datetime(2026, 10, 27, 17, 10), 'handyman': 'Marcus Reed', 'percent': 35, 'photos': 2, 'url': '/admin-portal/work-progress/evidence/',
         'details': 'Inspected the kitchen leak, isolated the water supply and removed the damaged pipe section. Site prepared for installation.'},
        {'report_date': date(2026, 10, 26), 'updated_at': datetime(2026, 10, 26, 15, 30), 'handyman': 'Marcus Reed', 'percent': 10, 'photos': 1, 'url': '/admin-portal/work-progress/evidence/',
         'details': 'Met the customer on site, confirmed the scope of work and photographed the damaged pipework.'},
    ],
}


def daily_reports(request):
    """Monitor Work Progress - Daily Work Reports."""
    return render(request, 'jobs/admin_daily_reports.html', {'page': DAILY_REPORTS})

# Sample data for Work Evidence & Completion Notes until the real job is connected
WORK_EVIDENCE = {
    'reference': 'JOB-1042',
    'title': 'Kitchen pipe repair and replacement',
    'reports_url': '/admin-portal/work-progress/reports/',
    'report_date': date(2026, 10, 29),
    'updated_at': datetime(2026, 10, 29, 16, 45),
    'handyman': 'Marcus Reed',
    'status': 'delayed',
    'status_label': 'Delayed',
    'photos': [
        {'caption': 'Pipework overview', 'filename': 'site_2910_01.jpg', 'url': ''},
        {'caption': 'New supply connection', 'filename': 'site_2910_02.jpg', 'url': ''},
        {'caption': 'Under-sink joint detail', 'filename': 'site_2910_03.jpg', 'url': ''},
    ],
    'notes': 'Main pipework installed and initial leak checks completed. A replacement elbow fitting is required before the final pressure test. Completion is delayed until the part arrives.',
    'is_flagged': False,
    'flag_reason': '',
    'flag_url': '',
}


def work_evidence(request):
    """Monitor Work Progress - Work Evidence & Completion Notes."""
    return render(request, 'jobs/admin_work_evidence.html', {'page': WORK_EVIDENCE})

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