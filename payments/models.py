from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

User = settings.AUTH_USER_MODEL

# Replace 'bookings.ServiceRequest' with the real name from the bookings owner.
# This file assumes that model has `customer` and `status` fields.


class Quotation(models.Model):
    """One fixed customer-facing quotation in MUR for a service request."""

    DRAFT, SENT, ACCEPTED, DECLINED, CANCELLED = 'draft', 'sent', 'accepted', 'declined', 'cancelled'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (SENT, 'Sent to customer'),
        (ACCEPTED, 'Accepted'),
        (DECLINED, 'Declined'),
        (CANCELLED, 'Cancelled'),
    ]

    request = models.ForeignKey('bookings.ServiceRequest', on_delete=models.PROTECT, related_name='quotations')
    work_description = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)   # MUR, one fixed total
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='quotations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # Only one live quotation per request
            models.UniqueConstraint(
                fields=['request'],
                condition=Q(status__in=['draft', 'sent', 'accepted']),
                name='one_live_quotation_per_request',
            ),
        ]

    def __str__(self):
        return f"Quotation {self.pk} - MUR {self.total_amount}"

    # ---- workflow ----
    def send(self):
        if self.status != self.DRAFT:
            raise ValidationError("Only a draft quotation can be sent.")
        self.status = self.SENT
        self.save()

    def accept(self, by):
        self._respond(by, self.ACCEPTED)

    def decline(self, by):
        self._respond(by, self.DECLINED)

    def _respond(self, by, new_status):
        from django.utils import timezone
        if self.status != self.SENT:
            raise ValidationError("Only a sent quotation can be accepted or declined.")
        if by != self.request.customer:
            raise ValidationError("Only the customer who made the request can respond.")
        self.status = new_status
        self.responded_at = timezone.now()
        self.save()

    # ---- paid / unpaid state for bookings and reports ----
    @property
    def is_paid(self):
        return hasattr(self, 'payment')

    @property
    def payment_state(self):
        return 'paid' if self.is_paid else 'unpaid'


class Payment(models.Model):
    """The full offline payment, recorded by an administrator. No online gateway."""

    METHOD_CHOICES = [('cash', 'Cash'), ('bank_transfer', 'Bank transfer')]

    # OneToOne means a second full payment for the same quotation is rejected
    quotation = models.OneToOneField(Quotation, on_delete=models.PROTECT, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_received = models.DateField()
    method = models.CharField(max_length=15, choices=METHOD_CHOICES)
    reference = models.CharField(max_length=60, blank=True)               # optional
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments_recorded')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.pk} - MUR {self.amount}"

    def clean(self):
        errors = {}
        q = self.quotation if self.quotation_id else None
        if q is not None:
            if q.status != Quotation.ACCEPTED:
                errors['quotation'] = "Payment can only be recorded for an accepted quotation."
            elif q.request.status == 'cancelled':
                errors['quotation'] = "Payment cannot be recorded for a cancelled request."
            if self.amount is not None and self.amount != q.total_amount:
                errors['amount'] = "The amount must equal the full quotation total."
        if self.recorded_by_id and getattr(self.recorded_by, 'role', None) != 'admin':
            errors['recorded_by'] = "Only an administrator can record a payment."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()          # always apply the rules, including duplicates
        super().save(*args, **kwargs)
