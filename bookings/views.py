"""Service request and appointment workflows."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from dashboard.permissions import role_required
from jobs.models import Job
from payments.models import LabourEstimate, Quotation

from .forms import ServiceRequestForm
from .models import Appointment, ServiceRequest, ServiceRequestAssignment
from .services import (
    cancel_appointment, confirm_appointment, create_appointment_proposal,
    forward_request, notify_customer_rejection, propose_reschedule,
    respond_to_appointment, respond_to_assignment,
)

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
    if sr.status == ServiceRequest.STATUS_REVIEWING and latest and sr.chosen_handyman_id != latest.handyman_id:
        return 'review'
    if latest is None or latest.status == ServiceRequestAssignment.STATUS_WITHDRAWN:
        return 'review'
    return {ServiceRequestAssignment.STATUS_SENT: 'forwarded',
            ServiceRequestAssignment.STATUS_ACCEPTED: 'accepted',
            ServiceRequestAssignment.STATUS_REJECTED: 'rejected'}[latest.status]


def _chosen(sr, latest):
    """Show the persisted customer choice or the latest forwarded handyman."""
    if latest and sr.chosen_handyman_id == latest.handyman_id:
        return latest.handyman, False
    if latest and sr.status != ServiceRequest.STATUS_REVIEWING:
        return latest.handyman, False
    return sr.chosen_handyman, False


def _preferred(sr):
    if not sr.preferred_date:
        return 'Not given'
    slot = f' · {sr.get_preferred_slot_display()}' if sr.preferred_slot else ''
    return f'{sr.preferred_date:%d %b %Y}{slot}'


def _quotation_step(sr):
    """After the handyman accepts: where the labour estimate / service quotation stands (FR-A-9 part A).

    Returns (text, button label, url); no button while the admin can only wait. Estimates open
    their own pop-up on the Labour estimates tab (#est-<id>).
    """
    quote = (sr.quotations.filter(quotation_type=Quotation.LABOUR).exclude(status=Quotation.CANCELLED)
             .order_by('-created_at').first())
    if quote:
        return ('The service quotation is prepared. Follow it in Service Quotations.', 'View Quotation',
                reverse('payments:quotation_detail_admin', args=[quote.pk]))
    est = sr.labour_estimates.order_by('-created_at').first()
    if est is None:
        return ("Waiting for the handyman's labour estimate (after assessing the job).", '', '')
    estimate_url = reverse('payments:estimate_list') + f'#est-{est.pk}'
    if est.status == LabourEstimate.SUBMITTED:
        return ('The handyman sent a labour estimate. Review it.', 'Review Estimate', estimate_url)
    if est.status == LabourEstimate.APPROVED:
        return ('The labour estimate is approved. Prepare the service quotation.', 'Prepare Quotation',
                reverse('payments:quotation_create', args=[sr.pk]) + f'?estimate={est.pk}')
    if est.status == LabourEstimate.REVISION_REQUESTED:
        return ("Waiting for the handyman's revised labour estimate.", 'View Estimate', estimate_url)
    return ('The labour estimate was rejected.', 'View Estimate', estimate_url)


def _requests():
    return (ServiceRequest.objects.select_related('customer', 'chosen_handyman')
            .prefetch_related(Prefetch('handyman_responses', to_attr='responses',
                                       queryset=ServiceRequestAssignment.objects.select_related('handyman').order_by('-sent_at', '-pk')))
            .order_by('-created_at'))


@role_required('admin')
def admin_requests(request):
    """Manage Service Requests - list page."""
    rows = []
    for sr in _requests():
        latest = _latest(sr)
        state = _state(sr, latest)
        chosen, sample = _chosen(sr, latest)
        rows.append({
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
    handyman, sample = _chosen(sr, latest)
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
        'forward_url': reverse('bookings:admin_forward_request', args=[sr.pk]),
        'notify_url': reverse('bookings:admin_notify_rejection', args=[sr.pk]),
        # Accepted: the next step is the labour estimate / service quotation
        'quotation_step': _quotation_step(sr) if state == 'accepted' else None,
        'appointment_url': reverse('accounts_admin:appointment_detail', args=[appointment.pk]) if appointment else '',
        'job_url': reverse('accounts_admin:work_progress_job', args=[job.pk]) if job else '',
        'show_response': request.GET.get('response') == '1' and state in ('accepted', 'rejected'),
        'list_url': reverse('bookings:admin_requests'),
    }
    return render(request, 'bookings/admin_service_request_detail.html', {'page': page})


@require_POST
@role_required('admin')
def admin_forward_request(request, pk):
    sr = get_object_or_404(ServiceRequest, pk=pk)
    try:
        forward_request(sr, request.user)
        messages.success(request, f'{sr.reference} was forwarded to the selected handyman.')
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    return redirect('bookings:admin_request_detail', pk=pk)


@require_POST
@role_required('admin')
def admin_notify_rejection(request, pk):
    sr = get_object_or_404(ServiceRequest, pk=pk)
    try:
        notify_customer_rejection(sr)
        messages.success(request, 'The customer has been notified to choose another handyman.')
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    return redirect('bookings:admin_request_detail', pk=pk)


@login_required
def my_requests(request):
    if request.user.role != 'customer':
        raise PermissionDenied
    return render(request, 'bookings/my_requests.html', {
        'requests': _requests().filter(customer=request.user),
    })


@login_required
def create_request(request):
    if request.user.role != 'customer':
        raise PermissionDenied
    form = ServiceRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        service_request = form.save(commit=False)
        service_request.customer = request.user
        service_request.status = ServiceRequest.STATUS_SUBMITTED
        service_request.contact_email = service_request.contact_email or request.user.email
        try:
            with transaction.atomic():
                service_request.full_clean()
                service_request.save()
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
        else:
            messages.success(request, f'Request {service_request.reference} was submitted.')
            return redirect('bookings:my_request_detail', pk=service_request.pk)
    return render(request, 'bookings/request_form.html', {'form': form})


@login_required
def my_request_detail(request, pk):
    if request.user.role != 'customer':
        raise PermissionDenied
    sr = get_object_or_404(_requests(), pk=pk, customer=request.user)
    latest = _latest(sr)
    appointment = sr.appointments.exclude(status=Appointment.STATUS_CANCELLED).order_by('-created_at').first()
    can_choose = bool(latest and latest.status == ServiceRequestAssignment.STATUS_REJECTED)
    handymen = User.objects.filter(role='handyman', is_active=True).exclude(
        service_request_assignments__service_request=sr,
    ).order_by('first_name', 'last_name', 'username') if can_choose else User.objects.none()
    return render(request, 'bookings/my_request_detail.html', {
        'service_request': sr, 'latest_assignment': latest, 'can_choose': can_choose,
        'handymen': handymen, 'appointment': appointment,
    })


@require_POST
@login_required
@transaction.atomic
def choose_another_handyman(request, pk):
    if request.user.role != 'customer':
        raise PermissionDenied
    sr = get_object_or_404(ServiceRequest.objects.select_for_update(), pk=pk, customer=request.user)
    latest = sr.handyman_responses.order_by('-sent_at', '-pk').first()
    if not latest or latest.status != ServiceRequestAssignment.STATUS_REJECTED:
        messages.error(request, 'You can choose another handyman after the current handyman declines.')
        return redirect('bookings:my_request_detail', pk=pk)
    handyman = get_object_or_404(User, pk=request.POST.get('handyman'), role='handyman', is_active=True)
    if sr.handyman_responses.filter(handyman=handyman).exists():
        messages.error(request, 'That handyman has already received this request. Choose another one.')
        return redirect('bookings:my_request_detail', pk=pk)
    sr.chosen_handyman = handyman
    sr.status = ServiceRequest.STATUS_REVIEWING
    sr.save(update_fields=['chosen_handyman', 'status', 'updated_at'])
    messages.success(request, 'Your new handyman choice was saved. The administrator will forward your request.')
    return redirect('bookings:my_request_detail', pk=pk)


@login_required
def handyman_requests(request):
    if request.user.role != 'handyman':
        raise PermissionDenied
    assignments = ServiceRequestAssignment.objects.filter(
        handyman=request.user,
    ).select_related('service_request', 'service_request__customer').order_by('-sent_at')
    return render(request, 'bookings/handyman_requests.html', {'assignments': assignments})


@require_POST
@login_required
def handyman_respond(request, pk):
    if request.user.role != 'handyman':
        raise PermissionDenied
    assignment = get_object_or_404(ServiceRequestAssignment, pk=pk, handyman=request.user)
    action = request.POST.get('action')
    if action not in ('accept', 'reject'):
        messages.error(request, 'Choose accept or decline.')
    else:
        try:
            respond_to_assignment(assignment, request.user, action == 'accept', request.POST.get('note', ''))
            messages.success(request, 'Your response was sent.')
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
    return redirect('bookings:handyman_requests')


@login_required
def my_appointments(request):
    if request.user.role != 'customer':
        raise PermissionDenied
    appointments = Appointment.objects.filter(
        service_request__customer=request.user,
    ).select_related('service_request', 'handyman').order_by('-created_at')
    return render(request, 'bookings/my_appointments.html', {'appointments': appointments})


@require_POST
@login_required
def appointment_respond(request, pk):
    if request.user.role != 'customer':
        raise PermissionDenied
    appointment = get_object_or_404(Appointment, pk=pk, service_request__customer=request.user)
    action = request.POST.get('action')
    if action not in ('accept', 'reject'):
        messages.error(request, 'Choose accept or decline.')
    else:
        try:
            respond_to_appointment(appointment, request.user, action == 'accept')
            messages.success(request, 'Your response was sent to HandyConnect.')
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
    return redirect('bookings:my_appointments')
