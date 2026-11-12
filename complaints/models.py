from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from jobs.models import Job, validate_file_size


class Complaint(models.Model):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In progress'),
        (RESOLVED, 'Resolved'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='complaints_submitted')
    # The other party on the job: the handyman for a customer complaint,
    # the customer for a handyman complaint.
    against = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='complaints_received')
    job = models.ForeignKey(
        Job, on_delete=models.PROTECT, related_name='complaints')
    subject = models.CharField(max_length=120)
    description = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    outcome = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} {self.subject}'

    def clean(self):
        if self.status == self.RESOLVED and not self.outcome.strip():
            raise ValidationError({'outcome': 'Record the investigation outcome before resolving.'})

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.reference:
            self.reference = f'CMP-{1000 + self.pk}'
            super().save(update_fields=['reference'])

    @property
    def is_resolved(self):
        return self.status == self.RESOLVED

    @property
    def badge(self):
        return {self.PENDING: 'ye', self.IN_PROGRESS: 'bl', self.RESOLVED: 'gr'}[self.status]

    def is_party(self, user):
        return user.pk in (self.submitted_by_id, self.against_id)


class ComplaintMessage(models.Model):
    """Admin enquiries and the parties' responses (FR-A-11.5 to 11.12)."""
    ENQUIRY = 'enquiry'
    RESPONSE = 'response'
    KIND_CHOICES = [(ENQUIRY, 'Enquiry from administrator'), (RESPONSE, 'Response')]

    complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    # Who an admin enquiry is addressed to. Empty for responses.
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class ComplaintEvidence(models.Model):
    """Supporting photos or documents (FR-H-7.8)."""
    complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='evidence')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    file = models.FileField(
        upload_to='complaint_evidence/%Y/%m/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'pdf']), validate_file_size])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']


class ComplaintLog(models.Model):
    """Append-only history of status changes (FR-A-11.4, NFR-H-11)."""
    complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='log')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
