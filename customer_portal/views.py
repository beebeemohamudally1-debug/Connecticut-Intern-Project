"""Customer portal pages: requests, appointments, notifications, profile, history.
Every view is customer-only (role_required) and only ever reads or writes the signed-in customer's own data."""
import re
from datetime import date
from zoneinfo import ZoneInfo
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from bookings.models import Appointment, ServiceRequest
from dashboard.permissions import role_required
from jobs.models import Job
from notifications.models import Notification
from payments.models import Payment
from services.models import ServiceArea, ServiceCategory

# ---------------------------------------------------------------- helpers
_STATUS = {
    'requested': ('Awaiting quote', 'warn'), 'submitted': ('Awaiting quote', 'warn'),
    'reviewing': ('Under review', 'info'), 'assigned': ('Matching a professional', 'info'),
    'booked': ('Scheduled', 'info'), 'completed': ('Completed', 'ok'), 'cancelled': ('Cancelled', 'bad'),
}
_APPT = {'pending': ('Pending', 'warn'), 'confirmed': ('Scheduled', 'info'),
         'cancelled': ('Cancelled', 'bad'), 'completed': ('Completed', 'ok')}
_SLOT = {'morning': 'Morning · 09–12', 'afternoon': 'Afternoon · 13–17'}


def _title(req):
    first = (req.problem_description or '').strip().split('\n')[0]
    return first[:60] or req.service_category or 'Service request'


def _fmt(d):
    return d.strftime('%b %d, %Y') if d else ''


def _initials(user):
    name = user.get_full_name() or user.username
    parts = name.split()
    return ''.join(p[0] for p in (parts[:1] + parts[-1:]))[:2].upper() if parts else '?'


def _row(req):
    label, tone = _STATUS.get(req.status, (req.get_status_display(), 'info'))
    q = req.quotations.order_by('-created_at').first()
    job = req.jobs.first()
    if q and q.status == 'sent':
        next_label, next_url = 'Review quotation', reverse('payments:quotation_detail', args=[q.pk])
    elif job:
        next_label, next_url = 'View job', reverse('jobs:detail', args=[job.pk])
    else:
        next_label, next_url = 'View request', reverse('customer_portal:request_submitted', args=[req.pk])
    return {'reference': req.reference, 'service': _title(req), 'title': _title(req), 'requested_at': _fmt(req.created_at),
            'status_label': label, 'status_tone': tone, 'next_label': next_label, 'next_url': next_url, 'url': next_url,
            'quote_label': f'QT-{q.pk} · {q.get_status_display()}' if q else 'Not issued',
            'amount': f'MUR {q.total_amount:,.0f}' if q and q.status == 'accepted' else ''}


def _appt_row(a):
    label, tone = _APPT.get(a.status, (a.get_status_display(), 'info'))
    req = a.service_request
    job = req.jobs.first()
    return {'reference': f'AP-{a.pk}', 'service': _title(req), 'title': _title(req), 'date': a.appointment_date.strftime('%a, %b %d'),
            'session': _SLOT.get(a.time_slot, a.get_time_slot_display()), 'address': req.service_address,
            'provider_name': a.handyman.get_full_name() or a.handyman.username, 'provider_initials': _initials(a.handyman),
            'status_label': label, 'status_tone': tone, 'status': a.status,
            'upcoming': a.appointment_date >= date.today() and a.status in ('pending', 'confirmed'),
            'url': reverse('jobs:detail', args=[job.pk]) if job else ''}


def _kind(n):
    t = (n.title + ' ' + n.notification_type).lower()
    if 'appointment' in t or 'visit' in t:
        return 'appointment'
    if 'payment' in t:
        return 'payment'
    return {'service_request': 'request', 'quotation': 'quotation', 'job': 'job', 'complaint': 'complaint',
            'feedback': 'feedback'}.get(n.notification_type, 'other')


# ---------------------------------------------------------------- requests
@role_required('customer')
def requests_list(request):
    qs = ServiceRequest.objects.filter(customer=request.user)
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(service_category__icontains=q) | Q(problem_description__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return render(request, 'customer/requests.html', {
        'requests': [_row(r) for r in qs], 'f': request.GET,
        'status_choices': [('requested', 'Awaiting quote'), ('reviewing', 'Under review'), ('assigned', 'Matching'),
                           ('booked', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]})


@role_required('customer')
def new_request(request):
    cats = list(ServiceCategory.objects.filter(is_active=True).values_list('name', flat=True))
    ctx = {'categories': cats, 'values': {}, 'errors': {}, 'service_areas': list(ServiceArea.objects.filter(is_active=True).values_list('name', flat=True))}
    if request.method == 'POST':
        v = {k: request.POST.get(k, '').strip() for k in (
            'service_category', 'service_type', 'title', 'problem_description', 'service_address',
            'contact_name', 'contact_phone', 'preferred_date', 'preferred_slot', 'access_notes')}
        err = {}
        for k, msg in (('service_category', 'Choose a category.'), ('title', 'Give your request a short title.'),
                       ('problem_description', 'Describe the issue.'), ('service_address', 'Enter the service address.'),
                       ('contact_name', 'Enter a contact name.'), ('contact_phone', 'Enter a contact number.'),
                       ('preferred_slot', 'Choose a session.')):
            if not v[k]:
                err[k] = msg
        if v['contact_phone'] and len(re.sub(r'\D', '', v['contact_phone'])) < 8:
            err['contact_phone'] = 'Enter a valid phone number.'
        if v['preferred_slot'] and v['preferred_slot'] not in _SLOT:
            err['preferred_slot'] = 'Choose a session.'
        pd = None
        try:
            pd = date.fromisoformat(v['preferred_date'])
            if pd < date.today():
                err['preferred_date'] = 'Choose a date from today onwards.'
        except ValueError:
            err['preferred_date'] = 'Choose a preferred date.'
        if err:
            ctx.update(values=v, errors=err, form_error='Please fix the highlighted fields.')
            return render(request, 'customer/new_request.html', ctx)
        desc = v['title'] + '\n\n' + v['problem_description']
        if v['service_type']:
            desc += f"\n\nService type: {v['service_type']}"
        if v['access_notes']:
            desc += f"\nAccess notes: {v['access_notes']}"
        sr = ServiceRequest.objects.create(
            customer=request.user, service_category=v['service_category'], problem_description=desc,
            service_address=v['service_address'], contact_name=v['contact_name'], contact_phone=v['contact_phone'],
            contact_email=request.user.email, preferred_date=pd, preferred_slot=v['preferred_slot'])
        for admin in User.objects.filter(role='admin', is_active=True):
            Notification.objects.create(recipient=admin, notification_type='service_request', title='New service request',
                                        message=f'{sr.reference} · {v["title"]}', url=reverse('bookings:admin_request_detail', args=[sr.pk]))
        Notification.objects.create(recipient=request.user, notification_type='service_request',
                                    title='Your service request was received',
                                    message=f'{sr.reference} · Admin will review your request and send a fixed quotation.',
                                    url=reverse('customer_portal:request_submitted', args=[sr.pk]))
        if request.FILES.getlist('attachments'):
            messages.info(request, 'Your request was saved. Photo uploads are not stored yet, so please share them with the service team directly.')
        return redirect('customer_portal:request_submitted', pk=sr.pk)
    ctx['initial_category'] = request.GET.get('category', '')
    ctx['values'] = {'contact_name': request.user.get_full_name(), 'contact_phone': request.user.phone, 'service_address': request.user.address}
    return render(request, 'customer/new_request.html', ctx)


@role_required('customer')
def request_submitted(request, pk):
    sr = get_object_or_404(ServiceRequest, pk=pk, customer=request.user)
    label, tone = _STATUS.get(sr.status, (sr.get_status_display(), 'info'))
    body = (sr.problem_description or '').split('\n\n', 1)
    req = {'reference': sr.reference, 'title': _title(sr), 'status_label': label, 'status_tone': tone,
           'description': body[1].split('\n\nService type')[0] if len(body) > 1 else body[0], 'category': sr.service_category,
           'address': sr.service_address, 'submitted_at': timezone.localtime(sr.created_at).strftime('%B %d, %Y at %I:%M %p'),
           'preferred_visit': f"{_fmt(sr.preferred_date)} · {_SLOT.get(sr.preferred_slot, '')}" if sr.preferred_date else ''}
    others = ServiceRequest.objects.filter(customer=request.user)[:5]
    return render(request, 'customer/request_submitted.html', {'req': req, 'requests': [_row(r) for r in others]})


# ---------------------------------------------------------------- appointments
@role_required('customer')
def appointments(request):
    qs = Appointment.objects.filter(service_request__customer=request.user).select_related('service_request', 'handyman')
    return render(request, 'customer/appointments.html', {'appointments': [_appt_row(a) for a in qs]})


# ---------------------------------------------------------------- notifications
@role_required('customer')
def notifications(request):
    items = request.user.notifications.all()[:100]
    rows = [{'id': n.pk, 'title': n.title, 'detail': n.message, 'unread': not n.is_read, 'kind': _kind(n),
             'when': timezone.localtime(n.created_at, ZoneInfo('Indian/Mauritius')).strftime('%b %d · %I:%M %p'),
             'url': reverse('customer_portal:notification_open', args=[n.pk])} for n in items]
    prefs = request.session.get('cp_prefs', {})
    return render(request, 'customer/notifications.html', {'notifications': rows, 'prefs': prefs})


@role_required('customer')
@require_POST
def notifications_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('customer_portal:notifications')


@role_required('customer')
def notification_open(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])
    return redirect(n.url if n.url.startswith('/') else 'customer_portal:notifications')


# ---------------------------------------------------------------- profile
@role_required('customer')
def profile(request):
    u = request.user
    ctx = {'errors': {}, 'service_areas': list(ServiceArea.objects.filter(is_active=True).values_list('name', flat=True)),
           'prefs': request.session.get('cp_prefs', {})}
    if request.method == 'POST':
        action = request.POST.get('action')
        p = request.POST
        if action == 'profile':
            fn, ln, em, ph = (p.get(k, '').strip() for k in ('first_name', 'last_name', 'email', 'phone'))
            addr, area = p.get('default_address', '').strip(), p.get('service_area', '').strip()
            err = {}
            if not fn:
                err['first_name'] = 'Enter your first name.'
            if not ln:
                err['last_name'] = 'Enter your last name.'
            try:
                validate_email(em)
                if User.objects.filter(email__iexact=em).exclude(pk=u.pk).exists():
                    err['email'] = 'That email is already in use.'
            except ValidationError:
                err['email'] = 'Enter a valid email address.'
            if len(re.sub(r'\D', '', ph)) < 8:
                err['phone'] = 'Enter a valid phone number.'
            if not addr:
                err['default_address'] = 'Enter your default address.'
            if err:
                ctx.update(errors=err, profile=dict(first_name=fn, last_name=ln, email=em, phone=ph, default_address=addr, service_area=area))
            else:
                u.first_name, u.last_name, u.email, u.phone, u.address = fn, ln, em, ph, addr
                u.region = ServiceArea.objects.filter(name=area).first() or u.region
                u.save()
                messages.success(request, 'Profile saved.')
                return redirect('customer_portal:profile')
        elif action == 'password':
            cur, new, conf = p.get('current_password', ''), p.get('new_password', ''), p.get('confirm_password', '')
            err = {}
            if not u.check_password(cur):
                err['current_password'] = 'Your current password is not correct.'
            if len(new) < 8:
                err['new_password'] = 'Use at least 8 characters.'
            if new != conf:
                err['confirm_password'] = 'The passwords do not match.'
            if err:
                ctx['errors'] = err
            else:
                u.set_password(new)
                u.save()
                update_session_auth_hash(request, u)
                messages.success(request, 'Password updated.')
                return redirect('customer_portal:profile')
        elif action == 'preferences':
            request.session['cp_prefs'] = {k: bool(p.get('pref_' + k)) for k in ('requests', 'payments', 'progress', 'email', 'sms', 'news')}
            messages.success(request, 'Preferences saved.')
            return redirect('customer_portal:profile')
    if 'profile' not in ctx:
        ctx['profile'] = dict(first_name=u.first_name, last_name=u.last_name, email=u.email, phone=u.phone,
                              default_address=u.address, service_area=u.region.name if u.region else '')
    return render(request, 'customer/profile.html', ctx)


# ---------------------------------------------------------------- history
@role_required('customer')
def history(request):
    f = request.GET
    reqs = ServiceRequest.objects.filter(customer=request.user)
    if f.get('q'):
        t = f['q'].strip()
        reqs = reqs.filter(Q(reference__icontains=t) | Q(service_category__icontains=t) | Q(problem_description__icontains=t))
    for key, lookup in (('from', 'created_at__date__gte'), ('to', 'created_at__date__lte')):
        try:
            reqs = reqs.filter(**{lookup: date.fromisoformat(f.get(key, ''))})
        except ValueError:
            pass
    records = []
    for r in reqs:
        a = r.appointments.order_by('-appointment_date').first()
        row = _row(r)
        records.append({'request_ref': r.reference, 'service': _title(r), 'url': row['url'], 'quotation_label': row['quote_label'],
                        'appointment_label': f"AP-{a.pk} · {a.appointment_date.strftime('%b %d')} {'AM' if a.time_slot == 'morning' else 'PM'}" if a else 'Not confirmed',
                        'progress_label': row['status_label']})
    payments = [{'job_ref': f'{p.quotation.request.reference} · PAY-{p.pk}', 'amount': f'{p.amount:,.0f}',
                 'paid_label': f"{p.date_received.strftime('%b %d')} · {p.get_method_display()}", 'status_label': 'Paid · Verified', 'status_tone': 'ok'}
                for p in Payment.objects.filter(quotation__request__customer=request.user).select_related('quotation__request')]
    feedback = []
    for j in Job.objects.filter(customer=request.user, status=Job.COMPLETED).select_related('review'):
        rv = getattr(j, 'review', None)
        feedback.append({'job_ref': j.reference, 'eligibility': f"Completed {j.completed_at.strftime('%b %d')}" if j.completed_at else 'Completed',
                         'feedback_label': 'Submitted privately' if rv else 'Share feedback',
                         'url': '' if rv else reverse('reviews:submit_review', args=[j.pk])})
    return render(request, 'customer/history.html', {'f': f, 'records': records, 'payments': payments, 'feedback': feedback})


# ---------------------------------------------------------------- dashboard data (used by dashboard.views.customer_dashboard)
def dashboard_context(user):
    reqs = ServiceRequest.objects.filter(customer=user)
    open_reqs = reqs.exclude(status__in=['completed', 'cancelled'])
    appts = Appointment.objects.filter(service_request__customer=user, status__in=['pending', 'confirmed'],
                                       appointment_date__gte=date.today()).select_related('service_request', 'handyman')
    nxt = appts.first()
    next_appt = None
    if nxt:
        r = _appt_row(nxt)
        next_appt = {'title': r['title'], 'status_label': r['status_label'], 'status_tone': r['status_tone'],
                     'provider_name': r['provider_name'], 'provider_initials': r['provider_initials'],
                     'date': r['date'], 'session': r['session'], 'address': r['address'],
                     'url': reverse('customer_portal:appointments')}
    updates = [{'title': n.title, 'detail': n.message, 'status_label': '', 'status_tone': 'info'}
               for n in user.notifications.all()[:3]]
    return {
        'first_name': user.first_name,
        'active_count': open_reqs.count(),
        'quote_ready_count': sum(1 for r in open_reqs if r.quotations.filter(status='sent').exists()),
        'upcoming_count': appts.count(),
        'next_visit': f"{nxt.appointment_date.strftime('%b %d')} · {nxt.get_time_slot_display()}" if nxt else '',
        'completed_count': reqs.filter(status='completed').count(),
        'feedback_count': user.submitted_reviews.count(),
        'recent_requests': [_row(r) for r in reqs[:4]],
        'updates': updates,
        'next_appointment': next_appt,
        'categories': list(ServiceCategory.objects.filter(is_active=True).values_list('name', flat=True)),
        'regions': list(ServiceArea.objects.filter(is_active=True).values_list('name', flat=True)),
    }
