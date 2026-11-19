"""Admin portal - Appointments (section 8): real data from bookings.Appointment.

These views only READ the database to show the pages (admin only).
BACKEND (bookings): there are no views yet that create, confirm, reschedule or cancel an
appointment, so those buttons save nothing and show a demo message. The places to connect
are marked "BACKEND" below and in the templates; see ADMIN_FRONTEND_README.md.
"""
import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from bookings.models import Appointment, ServiceRequest, ServiceRequestAssignment
from dashboard.permissions import role_required
from payments.models import Quotation, request_payment_state

from .admin_views import _initials, _person_name

SLOT_TIMES = {'morning': '08:00 - 12:00', 'afternoon': '13:00 - 17:00'}
TYPE_LABEL = {Appointment.TYPE_INSPECTION: 'Inspection', Appointment.TYPE_SERVICE: 'Service'}


def _ref(a):
    return f'APT-{1000 + a.pk}'


def _when(a):
    return f'{a.appointment_date:%d %b %Y} · {a.get_time_slot_display()}'


def _conflict(handyman, day, slot, exclude=None):
    """A confirmed appointment of the same handyman in the same date and slot (the model's rule)."""
    qs = Appointment.objects.filter(handyman=handyman, appointment_date=day, time_slot=slot,
                                    status=Appointment.STATUS_CONFIRMED)
    if exclude:
        qs = qs.exclude(pk=exclude.pk)
    return qs.select_related('service_request').first()


def _payment_checks(sr):
    """Quotation and payment checks for a service appointment (FR-A-9 part C).

    The labour quotation must be accepted and paid; a material quotation, if there is one,
    must be accepted and paid too.
    """
    quotes = list(sr.quotations.exclude(status__in=[Quotation.CANCELLED, Quotation.DECLINED])
                  .select_related('payment').order_by('-created_at')) if sr else []
    labour = next((q for q in quotes if q.quotation_type == Quotation.LABOUR), None)
    material = next((q for q in quotes if q.quotation_type == Quotation.MATERIAL), None)

    def state(q, needed):
        if not q:
            return ('Not issued', False) if needed else ('Not needed', True)
        if q.status != Quotation.ACCEPTED:
            return (q.get_status_display(), False)
        return ('Accepted', True)

    def paid(q, needed):
        if not q:
            return ('-', not needed)
        return ('Received', True) if q.is_paid else ('Not yet received', False)

    rows = [
        ('Service quotation', *state(labour, True)),
        ('Material quotation', *state(material, False)),
        ('Labour payment', *paid(labour, True)),
        ('Material payment', *paid(material, False)),
    ]
    ready = all(ok for _, _, ok in rows) and request_payment_state(sr) == 'paid'
    rows.append(('Full payment', 'Received' if ready else 'Not received', ready))
    return {'rows': [{'label': l, 'value': v, 'ok': ok} for l, v, ok in rows], 'ready': ready,
            'labour': labour, 'material': material}


def _row(a):
    sr = a.service_request
    return {
        'pk': a.pk, 'ref': _ref(a), 'request_ref': sr.reference, 'service': sr.service_category,
        'type': a.appointment_type, 'type_label': TYPE_LABEL[a.appointment_type],
        'customer': _person_name(sr.customer), 'handyman': _person_name(a.handyman),
        'date': a.appointment_date, 'slot': a.get_time_slot_display(), 'slot_key': a.time_slot,
        'status': a.status, 'status_label': a.get_status_display(),
        # pending and the date has passed: it was never confirmed
        'overdue': a.status == Appointment.STATUS_PENDING and a.appointment_date < timezone.localdate(),
        'url': reverse('accounts_admin:appointment_detail', args=[a.pk]),
    }


def _all():
    return (Appointment.objects.select_related('service_request', 'service_request__customer', 'handyman')
            .order_by('-appointment_date', 'time_slot'))


@role_required('admin')
def appointments(request):
    """Manage Appointments: every appointment, newest date first."""
    rows = [_row(a) for a in _all()]
    page = {
        'rows': rows,
        'counts': {'all': len(rows),
                   'inspection': sum(1 for r in rows if r['type'] == Appointment.TYPE_INSPECTION),
                   'service': sum(1 for r in rows if r['type'] == Appointment.TYPE_SERVICE)},
        'handymen': sorted({r['handyman'] for r in rows}),
        'schedule_inspection': reverse('accounts_admin:appointment_schedule', args=['inspection']),
        'schedule_service': reverse('accounts_admin:appointment_schedule', args=['service']),
    }
    return render(request, 'bookings/admin_appointments.html', {'page': page})


@role_required('admin')
def appointment_calendar(request):
    """Appointment Calendar: month, week or day (?view=month|week|day&date=YYYY-MM-DD)."""
    view = request.GET.get('view', 'month')
    if view not in ('month', 'week', 'day'):
        view = 'month'
    try:
        focus = date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        focus = timezone.localdate()

    if view == 'month':
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(focus.year, focus.month)
        start, end = weeks[0][0], weeks[-1][-1]
        prev_day = (focus.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_day = (focus.replace(day=28) + timedelta(days=4)).replace(day=1)
        title = f'{focus:%B %Y}'
    elif view == 'week':
        start = focus - timedelta(days=focus.weekday())
        end = start + timedelta(days=6)
        weeks = [[start + timedelta(days=i) for i in range(7)]]
        prev_day, next_day = start - timedelta(days=7), start + timedelta(days=7)
        title = f'{start:%d %b} – {end:%d %b %Y}'
    else:
        start = end = focus
        weeks = [[focus]]
        prev_day, next_day = focus - timedelta(days=1), focus + timedelta(days=1)
        title = f'{focus:%A %d %B %Y}'

    by_day = {}
    for a in _all().filter(appointment_date__range=(start, end)).exclude(status=Appointment.STATUS_CANCELLED):
        by_day.setdefault(a.appointment_date, []).append(_row(a))
    for items in by_day.values():
        items.sort(key=lambda r: r['slot_key'] != 'morning')

    today = timezone.localdate()
    grid = [[{'date': d, 'in_month': view != 'month' or d.month == focus.month, 'today': d == today,
              'items': by_day.get(d, [])} for d in week] for week in weeks]
    base = reverse('accounts_admin:appointment_calendar')
    page = {
        'view': view, 'title': title, 'grid': grid, 'focus': focus,
        'prev_url': f'{base}?view={view}&date={prev_day.isoformat()}',
        'next_url': f'{base}?view={view}&date={next_day.isoformat()}',
        'today_url': f'{base}?view={view}',
        'view_urls': {v: f'{base}?view={v}&date={focus.isoformat()}' for v in ('month', 'week', 'day')},
        'list_url': reverse('accounts_admin:appointments'),
        'slots': [('morning', 'Morning'), ('afternoon', 'Afternoon')],
    }
    return render(request, 'bookings/admin_appointment_calendar.html', {'page': page})


def _history(a):
    steps = [{'label': 'Appointment created', 'when': a.created_at, 'done': True}]
    if a.status == Appointment.STATUS_PENDING:
        steps.append({'label': 'Waiting for the customer to agree, then confirm', 'when': None, 'done': False})
    if a.confirmed_at:
        steps.append({'label': f'Confirmed by {_person_name(a.confirmed_by)}', 'when': a.confirmed_at, 'done': True})
    if a.status == Appointment.STATUS_CANCELLED:
        steps.append({'label': 'Cancelled', 'when': a.updated_at, 'done': True, 'stop': True})
    if a.status == Appointment.STATUS_COMPLETED:
        steps.append({'label': 'Completed', 'when': a.updated_at, 'done': True})
    return steps


@role_required('admin')
def appointment_detail(request, pk):
    """Appointment Details, with the Confirm, Reschedule and Cancel pop-ups."""
    a = get_object_or_404(_all(), pk=pk)
    sr = a.service_request
    conflict = _conflict(a.handyman, a.appointment_date, a.time_slot, exclude=a)
    checks = _payment_checks(sr) if a.appointment_type == Appointment.TYPE_SERVICE else None
    page = {
        **_row(a),
        'service_address': sr.service_address or '-', 'notes': a.notes,
        'customer_email': sr.customer.email or sr.contact_email or '-',
        'customer_phone': sr.contact_phone or getattr(sr.customer, 'phone', '') or '-',
        'customer_initials': _initials(sr.customer), 'handyman_initials': _initials(a.handyman),
        'preferred': f'{sr.preferred_date:%d %b %Y} · {sr.get_preferred_slot_display()}' if sr.preferred_date else '-',
        'when': _when(a), 'slot_time': SLOT_TIMES.get(a.time_slot, ''),
        'checks': checks,
        'quotation_url': reverse('payments:quotation_detail_admin', args=[checks['labour'].pk]) if checks and checks['labour'] else '',
        'history': _history(a),
        'conflict': {'ref': _ref(conflict), 'request_ref': conflict.service_request.reference} if conflict else None,
        'can_change': a.status in (Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED),
        'reschedule_url': reverse('accounts_admin:appointment_reschedule', args=[a.pk]),
        'list_url': reverse('accounts_admin:appointments'),
    }
    return render(request, 'bookings/admin_appointment_detail.html', {'page': page})


def _eligible_requests(kind):
    """Requests that can get this kind of appointment: a handyman has accepted the request; for a
    service appointment, the service quotation is accepted (ready = both quotations fully paid)."""
    taken = _scheduled(kind)
    accepted = (ServiceRequestAssignment.objects.filter(status=ServiceRequestAssignment.STATUS_ACCEPTED)
                .values_list('service_request_id', flat=True))
    qs = (ServiceRequest.objects.filter(pk__in=accepted).exclude(status__in=['cancelled', 'completed'])
          .select_related('customer').order_by('-created_at'))
    out = []
    for sr in qs:
        if sr.pk in taken:
            continue              # already has a pending or confirmed appointment of this kind
        if kind == Appointment.TYPE_SERVICE:
            checks = _payment_checks(sr)
            if not checks['labour'] or checks['labour'].status != Quotation.ACCEPTED:
                continue          # no accepted service quotation yet
            out.append((sr, checks['ready']))
        else:
            out.append((sr, True))
    return out


def _scheduled(kind):
    """Requests that already have a pending or confirmed appointment of this kind (request id -> appointment)."""
    active = Appointment.objects.filter(appointment_type=kind,
                                        status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED])
    return {a.service_request_id: a for a in active}


def _handymen(sr):
    return [a.handyman for a in sr.handyman_responses.filter(status=ServiceRequestAssignment.STATUS_ACCEPTED)
            .select_related('handyman')] if sr else []


def _busy(handymen):
    """Confirmed bookings of these handymen from today on (for the conflict check in the browser)."""
    return [{'handyman': a.handyman_id, 'date': a.appointment_date.isoformat(), 'slot': a.time_slot, 'ref': _ref(a)}
            for a in Appointment.objects.filter(handyman__in=handymen, status=Appointment.STATUS_CONFIRMED,
                                                appointment_date__gte=timezone.localdate())]


@role_required('admin')
def appointment_schedule(request, kind):
    """Schedule Inspection / Service Appointment (?request=<id> picks the service request)."""
    if kind not in (Appointment.TYPE_INSPECTION, Appointment.TYPE_SERVICE):
        return redirect('accounts_admin:appointments')
    sr = ServiceRequest.objects.filter(pk=request.GET.get('request') or request.POST.get('request')).select_related('customer').first()
    handymen = _handymen(sr)
    checks = _payment_checks(sr) if sr and kind == Appointment.TYPE_SERVICE else None
    existing = _scheduled(kind).get(sr.pk) if sr else None
    blocked = bool(checks and not checks['ready'])
    form = {'handyman': '', 'date': '', 'slot': '', 'notes': ''}
    conflict = None

    if request.method == 'POST' and sr and not blocked and not existing:
        form = {k: request.POST.get(k, '').strip() for k in form}
        handyman = next((h for h in handymen if str(h.pk) == form['handyman']), None)
        try:
            day = date.fromisoformat(form['date'])
        except ValueError:
            day = None
        if not handyman or not day or form['slot'] not in SLOT_TIMES:
            messages.error(request, 'Choose the handyman, the date and the time slot.')
        elif day < timezone.localdate():
            messages.error(request, 'The date cannot be in the past.')
        else:
            clash = _conflict(handyman, day, form['slot'])
            if clash:
                conflict = {'handyman': _person_name(handyman), 'requested': f'{day:%d %b %Y} · {form["slot"].title()}',
                            'ref': _ref(clash), 'booked': _when(clash), 'request_ref': clash.service_request.reference}
            else:
                # BACKEND: create the Pending appointment here (service_request, handyman, appointment_type,
                # appointment_date, time_slot, notes), then redirect to its Appointment Details page.
                messages.info(request, 'The slot is free. Not saved yet: scheduling is not in the backend (frontend demo only).')

    page = {
        'kind': kind, 'kind_label': TYPE_LABEL[kind],
        'requests': [{'pk': r.pk, 'label': f'{r.reference} · {_person_name(r.customer)} · {r.service_category}'
                               + ('' if ready else ' (not fully paid)')}
                     for r, ready in _eligible_requests(kind)],
        'request': {
            'pk': sr.pk, 'ref': sr.reference, 'customer': _person_name(sr.customer), 'service': sr.service_category,
            'address': sr.service_address or '-',
            'preferred': f'{sr.preferred_date:%d %b %Y} · {sr.get_preferred_slot_display()}' if sr.preferred_date else '-',
            'preferred_date': sr.preferred_date.isoformat() if sr.preferred_date else '',
            'preferred_slot': sr.preferred_slot,
        } if sr else None,
        'handymen': [{'pk': h.pk, 'name': _person_name(h)} for h in handymen],
        'busy': _busy(handymen),
        'existing': {'ref': _ref(existing), 'status': existing.get_status_display(),
                     'url': reverse('accounts_admin:appointment_detail', args=[existing.pk])} if existing else None,
        'checks': checks, 'blocked': blocked and not existing, 'locked': blocked or bool(existing), 'form': form, 'conflict': conflict,
        'slots': [(k, f'{k.title()} ({v})') for k, v in SLOT_TIMES.items()],
        'today': timezone.localdate().isoformat(),
        'list_url': reverse('accounts_admin:appointments'),
    }
    return render(request, 'bookings/admin_appointment_schedule.html', {'page': page})


@role_required('admin')
def appointment_reschedule(request, pk):
    """Propose Alternative Appointment: a new date and slot, back to Pending until the customer agrees."""
    a = get_object_or_404(_all(), pk=pk)
    if a.status not in (Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED):
        messages.error(request, 'This appointment can no longer be changed.')
        return redirect('accounts_admin:appointment_detail', pk=pk)
    sr = a.service_request
    form = {'date': '', 'slot': '', 'notes': 'Original slot unavailable; alternative proposed.'}
    conflict = None
    if request.method == 'POST':
        form = {k: request.POST.get(k, '').strip() for k in form}
        try:
            day = date.fromisoformat(form['date'])
        except ValueError:
            day = None
        if not day or form['slot'] not in SLOT_TIMES:
            messages.error(request, 'Choose the new date and time slot.')
        elif day < timezone.localdate():
            messages.error(request, 'The date cannot be in the past.')
        else:
            clash = _conflict(a.handyman, day, form['slot'], exclude=a)
            if clash:
                conflict = {'handyman': _person_name(a.handyman), 'requested': f'{day:%d %b %Y} · {form["slot"].title()}',
                            'ref': _ref(clash), 'booked': _when(clash), 'request_ref': clash.service_request.reference}
            else:
                # BACKEND: save the proposed date and slot (and the customer's answer once it exists),
                # then redirect to Appointment Details.
                messages.info(request, 'The slot is free. Not saved yet: rescheduling is not in the backend (frontend demo only).')
    page = {
        **_row(a), 'when': _when(a), 'form': form, 'conflict': conflict,
        'preferred': f'{sr.preferred_date:%d %b %Y} · {sr.get_preferred_slot_display()}' if sr.preferred_date else '-',
        'customer_email': sr.customer.email or sr.contact_email or '-',
        'customer_phone': sr.contact_phone or getattr(sr.customer, 'phone', '') or '-',
        'busy': _busy([a.handyman]), 'handyman_pk': a.handyman_id,
        'slots': [(k, f'{k.title()} ({v})') for k, v in SLOT_TIMES.items()],
        'today': timezone.localdate().isoformat(),
        'detail_url': reverse('accounts_admin:appointment_detail', args=[a.pk]),
    }
    return render(request, 'bookings/admin_appointment_reschedule.html', {'page': page})