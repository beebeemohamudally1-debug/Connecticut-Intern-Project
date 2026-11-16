from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# bookings.Appointment.clean() uses Quotation.ACCEPTED, Quotation.request and the
# reverse link `payment`. Do not rename them.


def _require_role(user, role, message):
    if getattr(user, 'role', None) != role:
        raise ValidationError(message)


# ====================================================== labour estimates
class LabourEstimate(models.Model):
    """The handyman's labour cost estimate, reviewed by the administrator."""

    SUBMITTED, APPROVED, REJECTED, REVISION_REQUESTED = 'submitted', 'approved', 'rejected', 'revision_requested'
    STATUS_CHOICES = [
        (SUBMITTED, 'Submitted'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (REVISION_REQUESTED, 'Revision requested'),
    ]

    request = models.ForeignKey('bookings.ServiceRequest', on_delete=models.PROTECT, related_name='labour_estimates')
    handyman = models.ForeignKey(User, on_delete=models.PROTECT, related_name='labour_estimates')
    amount = models.DecimalField(max_digits=10, decimal_places=2)          # MUR
    breakdown = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SUBMITTED)
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='estimates_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Estimate {self.pk} - MUR {self.amount}"

    def _review(self, by, new_status, note=''):
        _require_role(by, 'admin', "Only an administrator can review an estimate.")
        if self.status != self.SUBMITTED:
            raise ValidationError("Only a submitted estimate can be reviewed.")
        if new_status != self.APPROVED and not note.strip():
            raise ValidationError("Please give a reason.")
        self.status, self.admin_note = new_status, note
        self.reviewed_by, self.reviewed_at = by, timezone.now()
        self.save()

    def approve(self, by):
        self._review(by, self.APPROVED)

    def reject(self, by, note):
        self._review(by, self.REJECTED, note)

    def request_revision(self, by, note):
        self._review(by, self.REVISION_REQUESTED, note)

    def resubmit(self, by, amount, breakdown):
        if by != self.handyman:
            raise ValidationError("Only the handyman who made the estimate can revise it.")
        if self.status != self.REVISION_REQUESTED:
            raise ValidationError("Only an estimate with a revision request can be resubmitted.")
        self.amount, self.breakdown, self.status = amount, breakdown, self.SUBMITTED
        self.save()


# ============================================================ quotations
class Quotation(models.Model):
    """One fixed customer-facing quotation in MUR, either labour or material."""

    DRAFT, SENT, REVISION_REQUESTED, REVISED = 'draft', 'sent', 'revision_requested', 'revised'
    ACCEPTED, DECLINED, CANCELLED = 'accepted', 'declined', 'cancelled'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (SENT, 'Sent to customer'),
        (REVISION_REQUESTED, 'Revision requested'),
        (REVISED, 'Revised'),
        (ACCEPTED, 'Accepted'),
        (DECLINED, 'Declined'),
        (CANCELLED, 'Cancelled'),
    ]
    LABOUR, MATERIAL = 'labour', 'material'
    TYPE_CHOICES = [(LABOUR, 'Labour'), (MATERIAL, 'Material')]

    request = models.ForeignKey('bookings.ServiceRequest', on_delete=models.PROTECT, related_name='quotations')
    quotation_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=LABOUR)
    labour_estimate = models.ForeignKey(LabourEstimate, null=True, blank=True, on_delete=models.SET_NULL, related_name='quotations')
    work_description = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)   # MUR, one fixed total
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    revision_number = models.PositiveIntegerField(default=1)
    customer_note = models.TextField(blank=True)       # the customer's revision request
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='quotations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # One live quotation per request, per type (labour and material can both exist)
            models.UniqueConstraint(
                fields=['request', 'quotation_type'],
                condition=Q(status__in=['draft', 'sent', 'revision_requested', 'revised', 'accepted']),
                name='one_live_quotation_per_request_and_type',
            ),
        ]

    def __str__(self):
        return f"{self.get_quotation_type_display()} quotation {self.pk} - MUR {self.total_amount}"

    # ---- admin side ----
    def send(self):
        """Send a draft, or re-issue a revised quotation."""
        if self.status not in (self.DRAFT, self.REVISED):
            raise ValidationError("Only a draft or revised quotation can be sent.")
        if self.status == self.REVISED:
            self.revision_number += 1
        self.status = self.SENT
        self.save()

    def update(self, total_amount, work_description):
        if self.status not in (self.DRAFT, self.REVISED):
            raise ValidationError("Only a draft or revised quotation can be edited.")
        self.total_amount, self.work_description = total_amount, work_description
        self.save()

    def revise(self, by, total_amount, work_description):
        """The administrator answers a customer's revision request."""
        _require_role(by, 'admin', "Only an administrator can revise a quotation.")
        if self.status != self.REVISION_REQUESTED:
            raise ValidationError("Only a quotation with a revision request can be revised.")
        self.total_amount, self.work_description = total_amount, work_description
        self.status = self.REVISED
        self.save()

    def cancel(self, by):
        _require_role(by, 'admin', "Only an administrator can cancel a quotation.")
        if self.is_paid:
            raise ValidationError("A paid quotation cannot be cancelled.")
        if self.status in (self.CANCELLED, self.DECLINED):
            raise ValidationError("This quotation is already closed.")
        self.status = self.CANCELLED
        self.save()

    # ---- customer side ----
    def accept(self, by):
        self._respond(by, self.ACCEPTED)

    def decline(self, by):
        self._respond(by, self.DECLINED)

    def request_revision(self, by, note):
        if not (note or '').strip():
            raise ValidationError("Please explain what should change.")
        self._respond(by, self.REVISION_REQUESTED, note)

    def _respond(self, by, new_status, note=''):
        if self.status != self.SENT:
            raise ValidationError("Only a sent quotation can be answered.")
        if by != self.request.customer:
            raise ValidationError("Only the customer who made the request can respond.")
        self.status = new_status
        if note:
            self.customer_note = note
        self.responded_at = timezone.now()
        self.save()

    # ---- paid / unpaid state and payment readiness ----
    @property
    def is_paid(self):
        return hasattr(self, 'payment')

    @property
    def payment_state(self):
        return 'paid' if self.is_paid else 'unpaid'

    @property
    def readiness_issue(self):
        """Why this quotation cannot be paid yet. Empty text means it is ready."""
        if self.status != self.ACCEPTED:
            return "The quotation has not been accepted."
        if self.request.status == 'cancelled':
            return "The request is cancelled."
        if self.is_paid:
            return "It has already been paid."
        return ""

    @property
    def ready_for_payment(self):
        return not self.readiness_issue


def request_payment_state(service_request):
    """'none', 'unpaid', 'partial' or 'paid', across all accepted quotations of a request."""
    accepted = Quotation.objects.filter(request=service_request, status=Quotation.ACCEPTED)
    if not accepted.exists():
        return 'none'
    unpaid = accepted.filter(payment__isnull=True).exists()
    paid = accepted.filter(payment__isnull=False).exists()
    if unpaid:
        return 'partial' if paid else 'unpaid'
    return 'paid'


def request_fully_paid(service_request):
    return request_payment_state(service_request) == 'paid'


# ============================================================== payments
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


# ============================================================= materials
class MaterialPurchaseRequest(models.Model):
    """The handyman asks to buy materials. The administrator forwards it to the customer
    as a material quotation, or rejects it."""

    SUBMITTED, FORWARDED, REJECTED = 'submitted', 'forwarded', 'rejected'
    STATUS_CHOICES = [(SUBMITTED, 'Submitted'), (FORWARDED, 'Forwarded to customer'), (REJECTED, 'Rejected')]

    request = models.ForeignKey('bookings.ServiceRequest', on_delete=models.PROTECT, related_name='material_requests')
    handyman = models.ForeignKey(User, on_delete=models.PROTECT, related_name='material_requests')
    items = models.TextField()                                              # what to buy
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)   # MUR
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=SUBMITTED)
    admin_note = models.TextField(blank=True)
    quotation = models.OneToOneField(Quotation, null=True, blank=True, on_delete=models.SET_NULL, related_name='purchase_request')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='material_requests_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Material request {self.pk}"

    def _check(self, by):
        _require_role(by, 'admin', "Only an administrator can review a purchase request.")
        if self.status != self.SUBMITTED:
            raise ValidationError("Only a submitted purchase request can be reviewed.")

    def forward(self, by, total=None):
        """Create and send a material quotation to the customer."""
        self._check(by)
        quotation = Quotation(request=self.request, quotation_type=Quotation.MATERIAL, work_description=self.items,
                              total_amount=total or self.estimated_cost, created_by=by)
        with transaction.atomic():
            quotation.full_clean()
            quotation.save()
            quotation.send()
            self.quotation, self.status = quotation, self.FORWARDED
            self.reviewed_by, self.reviewed_at = by, timezone.now()
            self.save()
        return quotation

    def reject(self, by, note):
        self._check(by)
        if not (note or '').strip():
            raise ValidationError("Please give a reason.")
        self.status, self.admin_note = self.REJECTED, note
        self.reviewed_by, self.reviewed_at = by, timezone.now()
        self.save()


class MaterialReceipt(models.Model):
    """A receipt for materials the handyman bought, reviewed by the administrator."""

    SUBMITTED, APPROVED, REJECTED = 'submitted', 'approved', 'rejected'
    STATUS_CHOICES = [(SUBMITTED, 'Submitted'), (APPROVED, 'Approved'), (REJECTED, 'Rejected')]

    purchase_request = models.ForeignKey(MaterialPurchaseRequest, on_delete=models.PROTECT, related_name='receipts')
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='material_receipts')
    image = models.ImageField(upload_to='receipts/materials/')
    amount_spent = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=SUBMITTED)
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='receipts_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Receipt {self.pk} - MUR {self.amount_spent}"

    def clean(self):
        if self.purchase_request_id:
            quotation = self.purchase_request.quotation
            if quotation is None or quotation.status != Quotation.ACCEPTED:
                raise ValidationError("Receipts can be uploaded only after the customer accepts the material quotation.")

    def _review(self, by, new_status, note=''):
        _require_role(by, 'admin', "Only an administrator can review a receipt.")
        if self.status != self.SUBMITTED:
            raise ValidationError("Only a submitted receipt can be reviewed.")
        if new_status == self.REJECTED and not note.strip():
            raise ValidationError("Please give a reason.")
        self.status, self.admin_note = new_status, note
        self.reviewed_by, self.reviewed_at = by, timezone.now()
        self.save()

    def approve(self, by):
        self._review(by, self.APPROVED)

    def reject(self, by, note):
        self._review(by, self.REJECTED, note)
