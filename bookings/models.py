from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ServiceRequest(models.Model):
    SLOT_MORNING = 'morning'
    SLOT_AFTERNOON = 'afternoon'
    SLOT_CHOICES = [
        (SLOT_MORNING, 'Morning'),
        (SLOT_AFTERNOON, 'Afternoon'),
    ]

    STATUS_SUBMITTED = 'submitted'
    STATUS_REVIEWING = 'reviewing'
    STATUS_ASSIGNED = 'assigned'
    STATUS_BOOKED = 'booked'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_REVIEWING, 'Under review'),
        (STATUS_ASSIGNED, 'Sent to handymen'),
        (STATUS_BOOKED, 'Booked'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='service_requests',
        limit_choices_to={'role': 'customer'},
    )
    service_category = models.CharField(max_length=100)
    problem_description = models.TextField()
    service_address = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField(blank=True)
    preferred_date = models.DateField()
    preferred_slot = models.CharField(max_length=10, choices=SLOT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)

    # Payment transactions are not modeled in the payments app yet. These fields
    # record the admin's confirmation that the full amount has been received.
    full_payment_received_at = models.DateTimeField(null=True, blank=True)
    payment_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payments_recorded_for_requests',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} {self.service_category}'

    def clean(self):
        if self.customer_id and self.customer.role != 'customer':
            raise ValidationError({'customer': 'The selected user is not a customer.'})
        if bool(self.full_payment_received_at) != bool(self.payment_recorded_by_id):
            raise ValidationError(
                'Record both the full payment time and the administrator who recorded it.'
            )

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.reference:
            self.reference = f'SR-{1000 + self.pk}'
            super().save(update_fields=['reference'])


class ServiceRequestAssignment(models.Model):
    STATUS_SENT = 'sent'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_WITHDRAWN = 'withdrawn'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.PROTECT,
        related_name='handyman_responses',
    )
    handyman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='service_request_assignments',
        limit_choices_to={'role': 'handyman'},
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SENT)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='service_requests_sent',
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    response_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-sent_at']
        constraints = [
            models.UniqueConstraint(
                fields=['service_request', 'handyman'],
                name='one_handyman_offer_per_request',
            ),
        ]

    def __str__(self):
        return f'{self.service_request.reference} → {self.handyman}'

    def clean(self):
        if self.handyman_id and self.handyman.role != 'handyman':
            raise ValidationError({'handyman': 'The selected user is not a handyman.'})


class Appointment(models.Model):
    SLOT_CHOICES = ServiceRequest.SLOT_CHOICES

    TYPE_INSPECTION = 'inspection'
    TYPE_SERVICE = 'service'
    TYPE_CHOICES = [
        (TYPE_INSPECTION, 'Inspection visit'),
        (TYPE_SERVICE, 'Service appointment'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.PROTECT,
        related_name='appointments',
    )
    handyman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='appointments',
        limit_choices_to={'role': 'handyman'},
    )
    appointment_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default=TYPE_SERVICE)
    appointment_date = models.DateField()
    time_slot = models.CharField(max_length=10, choices=SLOT_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='appointments_confirmed',
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'time_slot']
        constraints = [
            models.UniqueConstraint(
                fields=['handyman', 'appointment_date', 'time_slot'],
                condition=Q(status='confirmed'),
                name='no_overlapping_confirmed_handyman_slots',
            ),
        ]

    def __str__(self):
        return f'{self.service_request.reference} · {self.appointment_date} · {self.handyman}'

    def clean(self):
        errors = {}
        if self.handyman_id and self.handyman.role != 'handyman':
            errors['handyman'] = 'The selected user is not a handyman.'

        if self.service_request_id and self.handyman_id:
            accepted = ServiceRequestAssignment.objects.filter(
                service_request_id=self.service_request_id,
                handyman_id=self.handyman_id,
                status=ServiceRequestAssignment.STATUS_ACCEPTED,
            ).exists()
            if not accepted:
                errors['handyman'] = 'The handyman must accept this service request first.'

        if self.status == self.STATUS_CONFIRMED and self.service_request_id:
            service_request = self.service_request
            if not service_request.full_payment_received_at:
                errors['status'] = 'Record full payment before confirming this appointment.'

        if self.status == self.STATUS_CONFIRMED and self.handyman_id and self.appointment_date:
            overlapping = Appointment.objects.filter(
                handyman_id=self.handyman_id,
                appointment_date=self.appointment_date,
                time_slot=self.time_slot,
                status=self.STATUS_CONFIRMED,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                errors['time_slot'] = 'This handyman already has a confirmed appointment in this slot.'

        if errors:
            raise ValidationError(errors)


class HandymanProfileRequest(models.Model):
    TYPE_SERVICE = 'service'
    TYPE_SKILL = 'skill'
    TYPE_CHOICES = [
        (TYPE_SERVICE, 'Service'),
        (TYPE_SKILL, 'Skill'),
    ]

    ACTION_ADD = 'add'
    ACTION_MODIFY = 'modify'
    ACTION_REMOVE = 'remove'
    ACTION_CHOICES = [
        (ACTION_ADD, 'Add'),
        (ACTION_MODIFY, 'Modify'),
        (ACTION_REMOVE, 'Remove'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    handyman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='profile_change_requests',
        limit_choices_to={'role': 'handyman'},
    )
    request_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    current_value = models.CharField(max_length=120, blank=True)
    requested_value = models.CharField(max_length=120, blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='handyman_profile_requests_reviewed',
    )

    class Meta:
        ordering = ['status', '-submitted_at']

    def __str__(self):
        value = self.requested_value or self.current_value
        return f'{self.handyman} · {self.get_action_display()} {self.get_request_type_display()}: {value}'

    def clean(self):
        if self.handyman_id and self.handyman.role != 'handyman':
            raise ValidationError({'handyman': 'The selected user is not a handyman.'})
        if self.action in (self.ACTION_ADD, self.ACTION_MODIFY) and not self.requested_value.strip():
            raise ValidationError({'requested_value': 'Enter the requested service or skill.'})
        if self.action in (self.ACTION_MODIFY, self.ACTION_REMOVE) and not self.current_value.strip():
            raise ValidationError({'current_value': 'Enter the current service or skill.'})
