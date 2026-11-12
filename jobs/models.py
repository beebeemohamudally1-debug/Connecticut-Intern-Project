from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (FileExtensionValidator, MaxValueValidator)
from django.db import models
from django.utils import timezone

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB, as in the registration rules


def validate_file_size(f):
    if f.size > MAX_UPLOAD_BYTES:
        raise ValidationError('File must be 5 MB or smaller.')


class Job(models.Model):
    ASSIGNED = 'assigned'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (ASSIGNED, 'Assigned'),
        (IN_PROGRESS, 'In progress'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]
    OPEN_STATUSES = (ASSIGNED, IN_PROGRESS)

    PAYOUT_NONE = 'none'
    PAYOUT_WAITING = 'waiting_for_payout'
    PAYOUT_FINISHED = 'finished_work'
    PAYOUT_CHOICES = [
        (PAYOUT_NONE, '-'),
        (PAYOUT_WAITING, 'Waiting for payout'),
        (PAYOUT_FINISHED, 'Finished work'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    # Link to the booking/quotation made by the bookings app. Replace with a
    # ForeignKey once bookings.ServiceRequest exists.
    request_ref = models.CharField(max_length=30, blank=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='customer_jobs', limit_choices_to={'role': 'customer'})
    handyman = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='handyman_jobs', limit_choices_to={'role': 'handyman'})
    service_name = models.CharField(max_length=100)
    description = models.TextField()
    address = models.CharField(max_length=255)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=ASSIGNED)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    payout_stage = models.CharField(max_length=20, choices=PAYOUT_CHOICES, default=PAYOUT_NONE)

    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)
    flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+')
    flagged_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} {self.service_name}'

    def clean(self):
        if self.customer_id and self.customer.role != 'customer':
            raise ValidationError({'customer': 'This user is not a customer.'})
        if self.handyman_id and self.handyman.role != 'handyman':
            raise ValidationError({'handyman': 'This user is not a handyman.'})

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.reference:
            self.reference = f'JOB-{1000 + self.pk}'
            super().save(update_fields=['reference'])

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @property
    def is_delayed(self):
        """Open job past its due date (FR-A-6.5)."""
        return bool(self.due_date and self.is_open and self.due_date < timezone.localdate())

    @property
    def badge(self):
        return {self.ASSIGNED: 'bl', self.IN_PROGRESS: 'ye',
                self.COMPLETED: 'gr', self.CANCELLED: 're'}[self.status]


class TimeLog(models.Model):
    """Arrival and clock-out times recorded by the handyman (FR-H-5.3)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='time_logs')
    arrived_at = models.DateTimeField()
    clocked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-arrived_at']

    def clean(self):
        if self.clocked_out_at and self.arrived_at and self.clocked_out_at < self.arrived_at:
            raise ValidationError('Clock-out time cannot be before arrival time.')

    @property
    def duration(self):
        return (self.clocked_out_at - self.arrived_at) if self.clocked_out_at else None

    @property
    def hours(self):
        d = self.duration
        return round(d.total_seconds() / 3600, 2) if d else None


class ProgressReport(models.Model):
    """One daily work report per job per day (FR-H-5.7, FR-A-6.3)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='reports')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    report_date = models.DateField(default=timezone.localdate)
    details = models.TextField()
    percent_complete = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-report_date']
        constraints = [models.UniqueConstraint(fields=['job', 'report_date'], name='one_report_per_job_day')]


class WorkEvidence(models.Model):
    """Photo of the work (FR-A-6.4)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='evidence')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    image = models.ImageField(
        upload_to='job_evidence/%Y/%m/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']), validate_file_size])
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
