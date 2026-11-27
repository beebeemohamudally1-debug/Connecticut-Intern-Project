"""Admin portal - Manage Service Requests (FR-A-4): real data from bookings.ServiceRequest.

These views only READ the database (admin only). The customer's request and the handyman's
answer (ServiceRequestAssignment) are shown as they are.
BACKEND (bookings): there are no views yet to forward a request to a handyman or to notify the
customer after a rejection, so those buttons save nothing and show a demo message (marked
"BACKEND" in the templates). ServiceRequest also has no field for the handyman the customer
chose, so requests not sent yet show a SAMPLE choice (see _chosen). See ADMIN_FRONTEND_README.md.
"""
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from dashboard.permissions import role_required
from jobs.models import Job
from accounts.models import HandymanProfile
from payments.models import LabourEstimate, Quotation, request_payment_state
from payments.subscriptions import has_active_subscription, subscribed_handymen

from .models import Appointment, ServiceRequest, ServiceRequestAssignment

# Page state -> label shown in the list and on the details page
STATES = {
    'review': 'Needs review',      # not sent to a handyman yet (or the last one was withdrawn)
    'forwarded': 'Forwarded',      # sent, waiting for the handyman's answer
    'accepted': 'Accepted',
    'rejected': 'Rejected',
    'booked': 'Booked',
    'completed': 'Completed',
    'cancelled': 'Cancelled',
}


def _name(user):
    return (user.get_full_name() or user.username) if user else ''


def _latest(sr):
    """The handyman the request was last sent to (prefetched, newest first), or None."""
    return sr.responses[0] if sr.responses else None


def _state(sr, latest):
    if sr.status in (ServiceRequest.STATUS_CANCELLED, ServiceRequest.STATUS_COMPLETED, ServiceRequest.STATUS_BOOKED):
        return sr.status
    if latest is None or latest.status == ServiceRequestAssignment.STATUS_WITHDRAWN:
        return 'review'
    return {ServiceRequestAssignment.STATUS_SENT: 'forwarded',
            ServiceRequestAssignment.STATUS_ACCEPTED: 'accepted',
            ServiceRequestAssignment.STATUS_REJECTED: 'rejected'}[latest.status]


def _sample_handymen():
    """Handymen a customer can choose: approved, not suspended and with a paid subscription (listed in search)."""
    return list(subscribed_handymen().filter(is_suspended=False, handyman_profile__status=HandymanProfile.STATUS_ACTIVE)
                .order_by('pk'))


def _chosen(sr, latest, sample_handymen):
    """The handyman the customer chose, and whether it is sample data.

    Once the request is sent, it is the handyman it was sent to (real data).
    BACKEND (bookings): add the customer's chosen handyman to ServiceRequest (for example a
    `chosen_handyman` ForeignKey) and return it here; until then a SAMPLE handyman is shown for
    requests that were not sent yet.
    """
    if latest:
        return latest.handyman, False
    if not sample_handymen:
        return None, False
    return sample_handymen[sr.pk % len(sample_handymen)], True


def _forward_block(handyman):
    """Why the request cannot be forwarded to this handyman ('' when it can): not approved, or no paid subscription."""
    if handyman is None:
        return 'none'
    if not (handyman.is_active and not getattr(handyman, 'is_suspended', False)
            and HandymanProfile.objects.filter(user=handyman, status=HandymanProfile.STATUS_ACTIVE).exists()):
        return 'approval'
    return '' if has_active_subscription(handyman) else 'subscription'


def _preferred(sr):
    if not sr.preferred_date:
        return 'Not given'
    slot = f' · {sr.get_preferred_slot_display()}' if sr.preferred_slot else ''
    return f'{sr.preferred_date:%d %b %Y}{slot}'


def _quotation_step(sr):
    """After the handyman accepts: where the labour estimate / service quotation stands (FR-A-9 part A).

    Returns (text, button label, url, stage); no button while the admin can only wait. Estimates open
    their own pop-up on the Labour estimates tab (#est-<id>). stage is the short label on the list page.
    """
    quote = (sr.quotations.filter(quotation_type=Quotation.LABOUR).exclude(status=Quotation.CANCELLED)
             .order_by('-created_at').first())
    if quote:
        quote_url = reverse('payments:quotation_detail_admin', args=[quote.pk])
        if quote.status == Quotation.ACCEPTED:
            # After the customer accepts: payment (Payment Status), then the service appointment
            if request_payment_state(sr) != 'paid':
                return ('The customer accepted the quotation. Check the payment status: materials, invoice and payment.',
                        'Check Payment Status', reverse('accounts_admin:payment_status', args=[sr.pk]), 'Awaiting payment')
            service = sr.appointments.filter(appointment_type=Appointment.TYPE_SERVICE).exclude(
                status=Appointment.STATUS_CANCELLED).first()
            if service:
                return ('Fully paid. The service appointment is ' + service.get_status_display().lower() + '.',
                        'View Appointment', reverse('accounts_admin:appointment_detail', args=[service.pk]), 'Service booked')
            return ('Fully paid. Schedule the service appointment.', 'Schedule Service',
                    reverse('accounts_admin:appointment_schedule', args=['service']) + f'?request={sr.pk}', 'Ready to schedule')
        text = {
            Quotation.DRAFT: 'The service quotation is saved as a draft. Send it to the customer.',
            Quotation.REVISION_REQUESTED: 'The customer asked for changes to the quotation.',
            Quotation.DECLINED: 'The customer declined the quotation.',
        }.get(quote.status, "The quotation is with the customer. Waiting for their answer.")
        stage = {Quotation.DRAFT: 'Quote draft', Quotation.REVISION_REQUESTED: 'Quote changes asked',
                 Quotation.DECLINED: 'Quote declined'}.get(quote.status, 'Quote sent')
        return (text, 'View Quotation', quote_url, stage)
    est = sr.labour_estimates.order_by('-created_at').first()
    if est is None:
        # The handyman may need to visit first: the inspection (with its fee) is scheduled here
        inspection = sr.appointments.filter(appointment_type=Appointment.TYPE_INSPECTION).exclude(
            status=Appointment.STATUS_CANCELLED).first()
        if inspection:
            return ('Inspection ' + inspection.get_status_display().lower() + ". The handyman sends the labour estimate after the visit.",
                    'View Inspection', reverse('accounts_admin:appointment_detail', args=[inspection.pk]), 'Inspection')
        return ("Waiting for the handyman's labour estimate. If they need to see the job first, schedule an inspection.",
                'Schedule Inspection', reverse('accounts_admin:appointment_schedule', args=['inspection']) + f'?request={sr.pk}',
                'Awaiting estimate')
    estimate_url = reverse('payments:estimate_list') + f'#est-{est.pk}'
    if est.status == LabourEstimate.SUBMITTED:
        return ('The handyman sent a labour estimate. Review it.', 'Review Estimate', estimate_url, 'Estimate to review')
    if est.status == LabourEstimate.APPROVED:
        return ('The labour estimate is approved. Prepare the service quotation.', 'Prepare Quotation',
                reverse('payments:quotation_create', args=[sr.pk]) + f'?estimate={est.pk}', 'Quote to prepare')
    if est.status == LabourEstimate.REVISION_REQUESTED:
        return ("Waiting for the handyman's revised labour estimate.", 'View Estimate', estimate_url, 'Estimate revising')
    return ("The labour estimate was rejected. Wait for the handyman's new estimate, or forward the request to another handyman.",
            'View Estimate', estimate_url, 'Estimate rejected')


def _requests():
    return (ServiceRequest.objects.select_related('customer')
            .prefetch_related(Prefetch('handyman_responses', to_attr='responses',
                                       queryset=ServiceRequestAssignment.objects.select_related('handyman').order_by('-sent_at', '-pk')))
            .order_by('-created_at'))


@role_required('admin')
def admin_requests(request):
    """Manage Service Requests - list page."""
    rows = []
    sample_handymen = _sample_handymen()
    for sr in _requests():
        latest = _latest(sr)
        state = _state(sr, latest)
        chosen, sample = _chosen(sr, latest, sample_handymen)
        rows.append({
            # Accepted: the stage it has reached (quote sent, ready to schedule, ...)
            'stage': _quotation_step(sr)[3] if state == 'accepted' else '',
            'ref': sr.reference, 'customer': _name(sr.customer), 'service': sr.service_category or 'Service request',
            'handyman': _name(chosen), 'sample': sample, 'state': state, 'label': STATES[state],
            'created': timezone.localdate(sr.created_at).isoformat(), 'created_label': f'{timezone.localtime(sr.created_at):%d %b %Y}',
            'url': reverse('bookings:admin_request_detail', args=[sr.pk]),
        })
    stats = {
        'all': len(rows),
        'review': sum(r['state'] == 'review' for r in rows),
        'forwarded': sum(r['state'] == 'forwarded' for r in rows),
        'accepted': sum(r['state'] == 'accepted' for r in rows),
    }
    services = sorted({r['service'] for r in rows})
    return render(request, 'bookings/admin_service_requests.html',
                  {'page': {'rows': rows, 'stats': stats, 'services': services, 'states': STATES}})


@role_required('admin')
def admin_request_detail(request, pk):
    """Service Request Details: the request, the handyman's answer and the next action."""
    sr = get_object_or_404(_requests(), pk=pk)
    latest = _latest(sr)
    state = _state(sr, latest)
    handyman, sample = _chosen(sr, latest, _sample_handymen())
    details = {
        'review': 'Not sent to a handyman yet.',
        'forwarded': "Waiting for the handyman's answer.",
        'accepted': 'Accepted the request.',
        'rejected': 'No reason given.',
    }
    appointment = sr.appointments.exclude(status=Appointment.STATUS_CANCELLED).order_by('-appointment_date').first()
    job = Job.objects.filter(service_request=sr).first()
    page = {
        'pk': sr.pk, 'ref': sr.reference, 'service': sr.service_category or 'Service request',
        'state': state, 'label': STATES[state],
        'customer': _name(sr.customer),
        'customer_url': reverse('accounts_admin:customer_detail', args=[sr.customer.pk]),
        'handyman': _name(handyman), 'sample': sample, 'preferred': _preferred(sr),
        'address': sr.service_address or 'Not given',
        'phone': sr.contact_phone or getattr(sr.customer, 'phone', '') or 'Not given',
        'contact': sr.contact_name or _name(sr.customer), 'email': sr.contact_email or sr.customer.email,
        'description': sr.problem_description or 'No description given.',
        'response': {
            'label': {'review': 'Not yet forwarded', 'forwarded': 'Waiting for answer'}.get(state)
                     or (latest.get_status_display() if latest else 'Not yet forwarded'),
            'tone': {'accepted': 'ok', 'rejected': 'bad'}.get(latest.status if latest else '', 'wait'),
            'details': (latest.response_note if latest and latest.response_note else details.get(state, '')),
            'on': f'{timezone.localtime(latest.responded_at):%d %b %Y}' if latest and latest.responded_at else '',
        },
        'handyman_pk': handyman.pk if handyman else '',
        # Only an approved, active handyman with a paid subscription can receive the request
        'handyman_block': _forward_block(handyman),
        'subscriptions_url': reverse('payments:subscription_list'),
        # Accepted: the next step is the labour estimate / service quotation
        'quotation_step': _quotation_step(sr) if state == 'accepted' else None,
        'appointment_url': reverse('accounts_admin:appointment_detail', args=[appointment.pk]) if appointment else '',
        'job_url': reverse('accounts_admin:work_progress_job', args=[job.pk]) if job else '',
        'show_response': request.GET.get('response') == '1' and state in ('accepted', 'rejected'),
        'list_url': reverse('bookings:admin_requests'),
    }
    return render(request, 'bookings/admin_service_request_detail.html', {'page': page})