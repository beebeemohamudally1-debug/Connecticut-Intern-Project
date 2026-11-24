"""Transactional service-request and appointment workflow operations."""
from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from jobs.models import Job
from notifications.models import Notification
from notifications.services import notify_admins
from payments.models import Quotation

from .models import Appointment, AppointmentEvent, ServiceRequest, ServiceRequestAssignment


def service_payment_readiness(service_request):
    """Require paid labour and, when issued, accepted and paid material quotations."""
    quotes = list(service_request.quotations.exclude(
        status__in=[Quotation.CANCELLED, Quotation.DECLINED]
    ).select_related('payment').order_by('-created_at'))
    labour = next((q for q in quotes if q.quotation_type == Quotation.LABOUR), None)
    material = next((q for q in quotes if q.quotation_type == Quotation.MATERIAL), None)

    checks = {
        'labour_exists': bool(labour),
        'labour_accepted': bool(labour and labour.status == Quotation.ACCEPTED),
        'labour_paid': bool(labour and labour.is_paid),
        'material_accepted': bool(not material or material.status == Quotation.ACCEPTED),
        'material_paid': bool(not material or material.is_paid),
    }
    checks['ready'] = all(checks.values())
    checks['labour'] = labour
    checks['material'] = material
    return checks


def _notify(user, notification_type, title, message, url):
    return Notification.objects.create(
        recipient=user,
        notification_type=notification_type,
        title=title,
        message=message,
        url=url,
    )


@transaction.atomic
def forward_request(service_request, admin_user):
    service_request = ServiceRequest.objects.select_for_update().select_related(
        'chosen_handyman'
    ).get(pk=service_request.pk)
    if service_request.status in (ServiceRequest.STATUS_CANCELLED, ServiceRequest.STATUS_COMPLETED,
                                  ServiceRequest.STATUS_BOOKED):
        raise ValidationError('This request cannot be forwarded in its current state.')
    handyman = service_request.chosen_handyman
    if not handyman or handyman.role != 'handyman' or not handyman.is_active:
        raise ValidationError('The customer must choose an active handyman before forwarding.')
    existing = ServiceRequestAssignment.objects.filter(
        service_request=service_request, handyman=handyman,
    ).first()
    if existing:
        raise ValidationError('This request has already been sent to the chosen handyman.')

    assignment = ServiceRequestAssignment(
        service_request=service_request,
        handyman=handyman,
        status=ServiceRequestAssignment.STATUS_SENT,
        sent_by=admin_user,
    )
    assignment.full_clean()
    assignment.save()
    service_request.status = ServiceRequest.STATUS_ASSIGNED
    service_request.save(update_fields=['status', 'updated_at'])
    _notify(
        handyman, 'service_request', 'New service request',
        f'{service_request.reference} is ready for your response.',
        reverse('bookings:handyman_requests'),
    )
    return assignment


@transaction.atomic
def respond_to_assignment(assignment, handyman, accept, note=''):
    assignment = ServiceRequestAssignment.objects.select_for_update().select_related(
        'service_request', 'service_request__customer'
    ).get(pk=assignment.pk)
    if assignment.handyman_id != handyman.pk:
        raise ValidationError('You can only respond to a request sent to you.')
    if assignment.status != ServiceRequestAssignment.STATUS_SENT:
        raise ValidationError('This request has already been answered.')
    assignment.status = (ServiceRequestAssignment.STATUS_ACCEPTED if accept
                         else ServiceRequestAssignment.STATUS_REJECTED)
    assignment.responded_at = timezone.now()
    assignment.response_note = note.strip()
    assignment.save(update_fields=['status', 'responded_at', 'response_note'])
    sr = assignment.service_request
    sr.status = ServiceRequest.STATUS_ASSIGNED if accept else ServiceRequest.STATUS_REVIEWING
    sr.save(update_fields=['status', 'updated_at'])
    if accept:
        _notify(
            sr.customer, 'service_request', 'Handyman accepted your request',
            f'{handyman.get_full_name() or handyman.username} accepted {sr.reference}.',
            reverse('bookings:my_request_detail', args=[sr.pk]),
        )
    else:
        notify_admins(
            'service_request', 'Handyman declined a request',
            f'{handyman.get_full_name() or handyman.username} declined {sr.reference}.',
            reverse('bookings:admin_request_detail', args=[sr.pk]) + '?response=1',
        )
    return assignment


@transaction.atomic
def notify_customer_rejection(service_request):
    latest = service_request.handyman_responses.select_related('handyman').order_by('-sent_at', '-pk').first()
    if not latest or latest.status != ServiceRequestAssignment.STATUS_REJECTED:
        raise ValidationError('There is no declined handyman response to notify about.')
    _notify(
        service_request.customer, 'service_request', 'Choose another handyman',
        f'The handyman declined {service_request.reference}. Please choose another handyman.',
        reverse('bookings:my_request_detail', args=[service_request.pk]),
    )


def _slot_start(appointment):
    start = time(8, 0) if appointment.time_slot == ServiceRequest.SLOT_MORNING else time(13, 0)
    return timezone.make_aware(datetime.combine(appointment.appointment_date, start))


@transaction.atomic
def create_appointment_proposal(*, service_request, handyman, appointment_type, day, slot, notes, actor):
    service_request = ServiceRequest.objects.select_for_update().select_related('customer').get(
        pk=service_request.pk
    )
    if appointment_type not in (Appointment.TYPE_INSPECTION, Appointment.TYPE_SERVICE):
        raise ValidationError('Choose a valid appointment type.')
    if day < timezone.localdate():
        raise ValidationError('The appointment date cannot be in the past.')
    if slot not in dict(ServiceRequest.SLOT_CHOICES):
        raise ValidationError('Choose a valid appointment time slot.')
    if not ServiceRequestAssignment.objects.filter(
        service_request=service_request, handyman=handyman,
        status=ServiceRequestAssignment.STATUS_ACCEPTED,
    ).exists():
        raise ValidationError('The handyman must accept the request first.')
    if appointment_type == Appointment.TYPE_SERVICE and not service_payment_readiness(service_request)['ready']:
        raise ValidationError('The service quotation and any material quotation must be accepted and fully paid.')
    if Appointment.objects.filter(
        service_request=service_request, appointment_type=appointment_type,
        status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED],
    ).exists():
        raise ValidationError('An active appointment of this type already exists for this request.')

    appointment = Appointment(
        service_request=service_request, handyman=handyman,
        appointment_type=appointment_type, appointment_date=day,
        time_slot=slot, status=Appointment.STATUS_PENDING,
        customer_response=Appointment.CUSTOMER_PENDING, notes=notes,
    )
    appointment.full_clean()
    appointment.save()
    AppointmentEvent.objects.create(
        appointment=appointment, event_type=AppointmentEvent.CREATED, actor=actor,
        detail=f'{day:%Y-%m-%d} {slot}',
    )
    link = reverse('bookings:my_appointments')
    for recipient in {service_request.customer, handyman}:
        _notify(recipient, 'appointment', 'Appointment proposal',
                f'An appointment was proposed for {service_request.reference} on {day:%d %b %Y} ({slot}).', link)
    return appointment


@transaction.atomic
def propose_reschedule(appointment, *, day, slot, notes, actor):
    appointment = Appointment.objects.select_for_update().select_related(
        'service_request', 'handyman', 'service_request__customer'
    ).get(pk=appointment.pk)
    if appointment.status not in (Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED):
        raise ValidationError('This appointment can no longer be changed.')
    if appointment.status == Appointment.STATUS_CONFIRMED and appointment.appointment_type == Appointment.TYPE_SERVICE:
        job = Job.objects.select_for_update().filter(
            service_request=appointment.service_request, handyman=appointment.handyman,
        ).exclude(status=Job.CANCELLED).order_by('-created_at').first()
        if job and job.status in (Job.IN_PROGRESS, Job.COMPLETED):
            raise ValidationError('This appointment cannot be rescheduled after work has started or completed.')
        if job:
            job.status = Job.CANCELLED
            job.save(update_fields=['status', 'updated_at'])
    if day < timezone.localdate() or slot not in dict(ServiceRequest.SLOT_CHOICES):
        raise ValidationError('Choose a valid future date and time slot.')
    old = f'{appointment.appointment_date:%Y-%m-%d} {appointment.time_slot}'
    appointment.appointment_date = day
    appointment.time_slot = slot
    appointment.notes = notes
    appointment.status = Appointment.STATUS_PENDING
    appointment.customer_response = Appointment.CUSTOMER_PENDING
    appointment.confirmed_at = None
    appointment.confirmed_by = None
    appointment.full_clean()
    appointment.save()
    AppointmentEvent.objects.create(
        appointment=appointment, event_type=AppointmentEvent.RESCHEDULED, actor=actor,
        detail=f'{old} -> {day:%Y-%m-%d} {slot}. {notes}'.strip(),
    )
    sr = appointment.service_request
    if appointment.appointment_type == Appointment.TYPE_SERVICE and sr.status == ServiceRequest.STATUS_BOOKED:
        sr.status = ServiceRequest.STATUS_ASSIGNED
        sr.save(update_fields=['status', 'updated_at'])
    for recipient in {sr.customer, appointment.handyman}:
        _notify(recipient, 'appointment', 'Appointment time changed',
                f'A new time was proposed for {sr.reference}: {day:%d %b %Y} ({slot}).',
                reverse('bookings:my_appointments'))
    return appointment


@transaction.atomic
def respond_to_appointment(appointment, customer, accept):
    appointment = Appointment.objects.select_for_update().select_related(
        'service_request', 'handyman'
    ).get(pk=appointment.pk)
    if appointment.service_request.customer_id != customer.pk:
        raise ValidationError('Only the customer who made this request can respond.')
    if appointment.status != Appointment.STATUS_PENDING:
        raise ValidationError('This appointment proposal is no longer awaiting a response.')
    if appointment.customer_response != Appointment.CUSTOMER_PENDING:
        raise ValidationError('You have already responded to this proposal.')
    appointment.customer_response = (Appointment.CUSTOMER_ACCEPTED if accept
                                     else Appointment.CUSTOMER_REJECTED)
    appointment.save(update_fields=['customer_response', 'updated_at'])
    kind = AppointmentEvent.CUSTOMER_ACCEPTED if accept else AppointmentEvent.CUSTOMER_REJECTED
    AppointmentEvent.objects.create(appointment=appointment, event_type=kind, actor=customer)
    notify_admins(
        'appointment', 'Customer responded to appointment',
        f'The customer {"accepted" if accept else "declined"} appointment APT-{1000 + appointment.pk}.',
        reverse('accounts_admin:appointment_detail', args=[appointment.pk]),
    )
    _notify(
        appointment.handyman, 'appointment', 'Customer responded to appointment',
        f'The customer {"accepted" if accept else "declined"} the appointment proposal for {appointment.service_request.reference}.',
        reverse('bookings:my_appointments'),
    )
    return appointment


@transaction.atomic
def confirm_appointment(appointment, admin_user):
    appointment = Appointment.objects.select_for_update().select_related(
        'service_request', 'service_request__customer', 'handyman'
    ).get(pk=appointment.pk)
    if appointment.status != Appointment.STATUS_PENDING:
        raise ValidationError('Only a pending appointment can be confirmed.')
    if appointment.customer_response != Appointment.CUSTOMER_ACCEPTED:
        raise ValidationError('Wait for the customer to accept this proposal before confirming it.')
    if appointment.service_request.status in (ServiceRequest.STATUS_CANCELLED, ServiceRequest.STATUS_COMPLETED):
        raise ValidationError('The related service request is no longer active.')
    if Appointment.objects.filter(
        handyman=appointment.handyman, appointment_date=appointment.appointment_date,
        time_slot=appointment.time_slot, status=Appointment.STATUS_CONFIRMED,
    ).exclude(pk=appointment.pk).exists():
        raise ValidationError('The handyman already has a confirmed appointment in this slot.')
    appointment.status = Appointment.STATUS_CONFIRMED
    appointment.confirmed_by = admin_user
    appointment.confirmed_at = timezone.now()
    appointment.full_clean()
    appointment.save()
    sr = appointment.service_request
    if appointment.appointment_type == Appointment.TYPE_SERVICE:
        sr.status = ServiceRequest.STATUS_BOOKED
        sr.save(update_fields=['status', 'updated_at'])
        active_job = Job.objects.filter(
            service_request=sr, status__in=[Job.ASSIGNED, Job.IN_PROGRESS, Job.COMPLETED],
        ).first()
        if not active_job:
            job = Job(
                service_request=sr, customer=sr.customer, handyman=appointment.handyman,
                service_name=sr.service_category or 'Service request',
                description=sr.problem_description or 'Service requested by customer.',
                address=sr.service_address, scheduled_start=_slot_start(appointment),
                due_date=appointment.appointment_date,
            )
            job.full_clean()
            job.save()
        else:
            active_job.scheduled_start = _slot_start(appointment)
            active_job.due_date = appointment.appointment_date
            active_job.save(update_fields=['scheduled_start', 'due_date', 'updated_at'])
    AppointmentEvent.objects.create(appointment=appointment, event_type=AppointmentEvent.CONFIRMED,
                                    actor=admin_user)
    for recipient in {sr.customer, appointment.handyman}:
        _notify(recipient, 'appointment', 'Appointment confirmed',
                f'Appointment APT-{1000 + appointment.pk} for {sr.reference} is confirmed.',
                reverse('bookings:my_appointments'))
    return appointment


@transaction.atomic
def cancel_appointment(appointment, admin_user, reason):
    appointment = Appointment.objects.select_for_update().select_related(
        'service_request', 'service_request__customer', 'handyman'
    ).get(pk=appointment.pk)
    reason = (reason or '').strip()
    if appointment.status not in (Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED):
        raise ValidationError('This appointment can no longer be cancelled.')
    if not reason:
        raise ValidationError('Give a reason for cancelling this appointment.')
    related_job = None
    if appointment.appointment_type == Appointment.TYPE_SERVICE:
        related_job = Job.objects.select_for_update().filter(
            service_request=appointment.service_request,
        ).exclude(status=Job.CANCELLED).order_by('-created_at').first()
    if related_job and related_job.status in (Job.IN_PROGRESS, Job.COMPLETED):
        raise ValidationError('An appointment cannot be cancelled after work has started or completed.')
    appointment.status = Appointment.STATUS_CANCELLED
    appointment.cancellation_reason = reason[:300]
    appointment.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
    if related_job:
        related_job.status = Job.CANCELLED
        related_job.save(update_fields=['status', 'updated_at'])
    sr = appointment.service_request
    if appointment.appointment_type == Appointment.TYPE_SERVICE and sr.status == ServiceRequest.STATUS_BOOKED:
        sr.status = ServiceRequest.STATUS_ASSIGNED
        sr.save(update_fields=['status', 'updated_at'])
    AppointmentEvent.objects.create(appointment=appointment, event_type=AppointmentEvent.CANCELLED,
                                    actor=admin_user, detail=reason[:300])
    for recipient in {sr.customer, appointment.handyman}:
        _notify(recipient, 'appointment', 'Appointment cancelled',
                f'Appointment APT-{1000 + appointment.pk} for {sr.reference} was cancelled: {reason[:200]}',
                reverse('bookings:my_appointments'))
    return appointment
