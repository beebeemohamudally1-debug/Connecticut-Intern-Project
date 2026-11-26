"""Handyman payouts.

After a job is completed and the customer's job invoice is cleared, the administrator pays the
handyman offline and records it here. The handyman then confirms that he received the money.

Kept in its own module so the quotation, invoice and receipt models are not touched. The one
line that loads it is at the bottom of payments/models.py.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

User = settings.AUTH_USER_MODEL
MAX_PROOF_BYTES = 5 * 1024 * 1024


def _require_role(user, role, message):
    if getattr(user, 'role', None) != role:
        raise ValidationError(message)


def _validate_proof_size(f):
    if f.size > MAX_PROOF_BYTES:
        raise ValidationError('The proof must be 5 MB or smaller.')


def _notify(user, title, message, url=''):
    """Best effort: a notification problem must never stop a payout."""
    try:
        from notifications.models import Notification
        Notification.objects.create(recipient=user, notification_type='job', title=title, message=message, url=url)
    except Exception:
        pass


def _money(value):
    return Decimal(value or 0).quantize(Decimal('0.01'))


# ============================================================ the model
class HandymanPayout(models.Model):
    """The payout to a handyman for one completed job, funded by the customer's cleared job invoice."""

    PAID, CONFIRMED = 'paid', 'confirmed'
    STATUS_CHOICES = [(PAID, 'Paid, waiting for confirmation'), (CONFIRMED, 'Confirmed by handyman')]
    METHOD_CHOICES = [('cash', 'Cash'), ('bank_transfer', 'Bank transfer')]

    number = models.CharField(max_length=20, unique=True, editable=False)
    # CASCADE on job and invoice so the demo data reset (seed_demo) can still delete jobs and invoices
    job = models.OneToOneField('jobs.Job', on_delete=models.CASCADE, related_name='payout')
    handyman = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payouts')
    invoice = models.ForeignKey('payments.Invoice', on_delete=models.CASCADE, related_name='payouts')
    labour_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)        # MUR
    materials_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)     # MUR
    amount = models.DecimalField(max_digits=10, decimal_places=2)                          # labour + materials
    date_paid = models.DateField()
    method = models.CharField(max_length=15, choices=METHOD_CHOICES)
    reference = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PAID)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payouts_recorded')
    recorded_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    proof_image = models.ImageField(
        upload_to='receipts/payouts/', blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']), _validate_proof_size])

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f'{self.number} - MUR {self.amount}'

    @property
    def is_confirmed(self):
        return self.status == self.CONFIRMED

    # ---- cross-check: what the customer paid against what the handyman receives ----
    @property
    def customer_paid(self):
        return self.invoice.total_amount

    @property
    def platform_margin(self):
        return self.customer_paid - self.amount

    @property
    def suggested(self):
        return suggested_amounts(self.job)

    @property
    def cross_check(self):
        """A short list of notes for the administrator. Empty means everything lines up."""
        notes = []
        labour, materials = self.suggested
        if labour is not None and self.labour_amount != labour:
            notes.append(f"Labour paid (MUR {self.labour_amount}) differs from the approved estimate (MUR {labour}).")
        if self.materials_amount != materials:
            notes.append(f"Materials paid (MUR {self.materials_amount}) differ from the approved receipts (MUR {materials}).")
        if self.platform_margin < 0:
            notes.append("The payout is more than the customer paid.")
        return notes

    # ---- rules ----
    @classmethod
    def blocker(cls, job):
        """Why this job cannot be paid out yet. Returns (invoice, message); message is '' when it can."""
        from .models import Invoice
        if job.status != 'completed':
            return None, "The job has not been completed."
        if job.service_request_id is None:
            return None, "This job is not linked to a service request, so there is no customer payment to pay from."
        invoice = Invoice.objects.filter(request_id=job.service_request_id, invoice_type=Invoice.JOB, status=Invoice.PAID).first()
        if invoice is None:
            return None, "The customer's payment has not been cleared yet."
        if cls.objects.filter(job=job).exists():
            return invoice, "This job has already been paid out."
        return invoice, ""

    @classmethod
    def record(cls, by, job, *, labour_amount, materials_amount, date_paid, method, reference=''):
        """The administrator records the offline payout."""
        from .models import DocumentCounter
        _require_role(by, 'admin', "Only an administrator can record a payout.")
        invoice, problem = cls.blocker(job)
        if problem:
            raise ValidationError(problem)
        labour, materials = _money(labour_amount), _money(materials_amount)
        if labour < 0 or materials < 0:
            raise ValidationError("Amounts cannot be negative.")
        total = labour + materials
        if total <= 0:
            raise ValidationError("The payout must be more than zero.")
        if total > invoice.total_amount:
            raise ValidationError(f"The payout cannot be more than the customer paid (MUR {invoice.total_amount}).")
        if date_paid > timezone.localdate():
            raise ValidationError("The payment date cannot be in the future.")
        if method not in dict(cls.METHOD_CHOICES):
            raise ValidationError("Choose how the handyman was paid.")
        with transaction.atomic():
            payout = cls.objects.create(
                number=DocumentCounter.next_number('PAY'), job=job, handyman=job.handyman, invoice=invoice,
                labour_amount=labour, materials_amount=materials, amount=total,
                date_paid=date_paid, method=method, reference=reference, recorded_by=by)
        from django.urls import reverse
        _notify(job.handyman, 'Payout recorded',
                f'A payout of MUR {total} for job {job.reference} was recorded. Please confirm that you received it.',
                reverse('payments:payout_detail', args=[payout.pk]))
        return payout

    def confirm(self, by, proof=None):
        """The handyman confirms he received the payout, with an optional proof of payment."""
        if by != self.handyman:
            raise ValidationError("Only the handyman who was paid can confirm this payout.")
        if self.status != self.PAID:
            raise ValidationError("This payout has already been confirmed.")
        if proof:
            self.proof_image = proof
            try:
                self.full_clean(exclude=['number'])
            except ValidationError as error:
                raise ValidationError(' '.join(error.messages))
        with transaction.atomic():
            self.status, self.confirmed_at = self.CONFIRMED, timezone.now()
            self.save()
            # The jobs app has a "Finished work" payout stage for exactly this moment
            from jobs.models import Job
            Job.objects.filter(pk=self.job_id).update(payout_stage=Job.PAYOUT_FINISHED)
        try:
            from notifications.services import notify_admins
            notify_admins('job', 'Payout confirmed', f'{self.handyman} confirmed payout {self.number}.')
        except Exception:
            pass


# ============================================================ helpers other code can use
def suggested_amounts(job):
    """(labour, materials) the handyman should receive. labour is None when no estimate is linked.

    labour    = the handyman's approved labour estimate behind the labour quotation
    materials = the total of his approved material receipts on the request
    """
    from .models import Invoice, MaterialReceipt
    labour = None
    invoice = Invoice.objects.filter(request_id=job.service_request_id, invoice_type=Invoice.JOB).exclude(status=Invoice.CANCELLED).first()
    if invoice and invoice.labour_quotation_id and invoice.labour_quotation.labour_estimate_id:
        estimate = invoice.labour_quotation.labour_estimate
        if estimate.status == 'approved':
            labour = estimate.amount
    spent = MaterialReceipt.objects.filter(
        purchase_request__request_id=job.service_request_id, purchase_request__handyman_id=job.handyman_id,
        status=MaterialReceipt.APPROVED).aggregate(total=Sum('amount_spent'))['total']
    return labour, _money(spent)


def jobs_ready_for_payout():
    """Completed jobs whose customer payment is cleared and that have not been paid out."""
    from jobs.models import Job
    from .models import Invoice
    return (Job.objects.filter(status='completed', payout__isnull=True, service_request__invoices__invoice_type=Invoice.JOB,
                               service_request__invoices__status=Invoice.PAID)
            .distinct().select_related('handyman', 'customer', 'service_request'))


def jobs_waiting_for_customer_payment():
    """Completed jobs where the customer has not cleared the job invoice yet."""
    from jobs.models import Job
    from .models import Invoice
    cleared = Invoice.objects.filter(invoice_type=Invoice.JOB, status=Invoice.PAID).values('request_id')
    return (Job.objects.filter(status='completed', payout__isnull=True).exclude(service_request_id__in=cleared)
            .select_related('handyman', 'customer'))


def handyman_earnings(handyman, year=None, month=None):
    """Figures for a handyman's earnings card. The dashboard owner can call this to show real numbers.

    paid_this_month         payouts paid in the month (default: this month), confirmed or not, in MUR
    confirmed_total         everything the handyman has confirmed receiving
    waiting_confirmation    paid out but not confirmed yet
    ready_for_payout        completed jobs the customer has paid for, waiting for the administrator
    waiting_for_customer    completed jobs the customer has not paid for yet
    """
    today = timezone.localdate()
    year, month = year or today.year, month or today.month
    mine = HandymanPayout.objects.filter(handyman=handyman)
    total = lambda qs: _money(qs.aggregate(t=Sum('amount'))['t'])
    return {
        'paid_this_month': total(mine.filter(date_paid__year=year, date_paid__month=month)),
        'confirmed_total': total(mine.filter(status=HandymanPayout.CONFIRMED)),
        'waiting_confirmation': total(mine.filter(status=HandymanPayout.PAID)),
        'ready_for_payout': jobs_ready_for_payout().filter(handyman=handyman).count(),
        'waiting_for_customer': jobs_waiting_for_customer_payment().filter(handyman=handyman).count(),
    }
