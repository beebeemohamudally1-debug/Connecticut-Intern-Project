"""Handyman subscriptions: a monthly or yearly fee, paid offline, invoiced automatically.

How it fits together
  * A subscription is paid through the normal Invoice -> InvoicePayment -> Receipt flow (invoice type
    'subscription', numbers SUB-2026-0001). Clearing the payment extends `expires_on`.
  * `expires_on` is the LAST day that is paid for. A handyman is listed and may take new requests only
    while expires_on >= today. There is no grace period.
  * Cancelling is allowed at any time. There is no refund; access continues until expires_on.
  * `run_daily()` (management command `run_subscriptions`) issues the next invoice before expiry and
    sends the reminders. Run it once a day.
  * Other code asks: has_active_subscription(user), subscribed_handymen(), @subscription_required.
Prices are in settings.py: SUBSCRIPTION_MONTHLY_FEE and SUBSCRIPTION_YEARLY_FEE (MUR).
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models, transaction
from django.shortcuts import redirect
from django.utils import timezone

MONTHLY, YEARLY = 'monthly', 'yearly'
PLAN_CHOICES = [(MONTHLY, 'Monthly'), (YEARLY, 'Yearly')]
PLAN_MONTHS = {MONTHLY: 1, YEARLY: 12}

ACTIVE, CANCELLING, AWAITING, LAPSED, CANCELLED, NEW = 'active', 'cancelling', 'awaiting', 'lapsed', 'cancelled', 'new'
STATE_LABELS = {
    ACTIVE: 'Active', CANCELLING: 'Active, ends at expiry', AWAITING: 'Awaiting payment',
    LAPSED: 'Lapsed', CANCELLED: 'Cancelled', NEW: 'Not subscribed',
}
# CSS class for the status pill (dashboard: approved = green, pending = amber, rejected = red, declined = grey)
STATE_TONES = {ACTIVE: 'approved', CANCELLING: 'pending', AWAITING: 'pending', LAPSED: 'rejected',
               CANCELLED: 'declined', NEW: 'declined'}

REMINDER_DAYS = (7, 3, 1, 0)          # days before expiry when a reminder is sent


# ------------------------------------------------------------------ prices and settings
def plan_price(plan):
    """Fee in MUR for a plan. Override with SUBSCRIPTION_MONTHLY_FEE / SUBSCRIPTION_YEARLY_FEE."""
    if plan not in PLAN_MONTHS:
        raise ValidationError("Choose the monthly or the yearly plan.")
    defaults = {MONTHLY: '1500.00', YEARLY: '15300.00'}              # yearly = 15% off 12 months
    names = {MONTHLY: 'SUBSCRIPTION_MONTHLY_FEE', YEARLY: 'SUBSCRIPTION_YEARLY_FEE'}
    return Decimal(str(getattr(settings, names[plan], defaults[plan])))


def plan_options():
    """The plans as the 'choose a plan' cards need them."""
    monthly_total = plan_price(MONTHLY) * PLAN_MONTHS[YEARLY]
    options = []
    for code, label in PLAN_CHOICES:
        price = plan_price(code)
        full = plan_price(MONTHLY) * PLAN_MONTHS[code]
        options.append({'code': code, 'label': label, 'price': price, 'months': PLAN_MONTHS[code],
                        'per_month': (price / PLAN_MONTHS[code]).quantize(Decimal('0.01')),
                        'saving': max(full - price, Decimal('0'))})
    return options


def invoice_days_before():
    """The renewal invoice is issued this many days before the paid period ends."""
    return int(getattr(settings, 'SUBSCRIPTION_INVOICE_DAYS_BEFORE', 7))


def first_due_days():
    """Days to pay the first invoice (and any invoice after a lapse). Nothing is listed until it is paid."""
    return int(getattr(settings, 'SUBSCRIPTION_FIRST_DUE_DAYS', 3))


def add_months(d, months):
    """The same day `months` later; the day is clamped for short months (31 Jan + 1 month = 28 Feb)."""
    index = d.month - 1 + months
    year, month = d.year + index // 12, index % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def money(amount):
    return f"MUR {amount:,.2f}"


# ------------------------------------------------------------------ models
class HandymanSubscription(models.Model):
    """One per handyman. History is kept by the invoices and receipts."""

    handyman = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='subscription',
                                    limit_choices_to={'role': 'handyman'})
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default=MONTHLY)
    expires_on = models.DateField(null=True, blank=True, help_text='Last day that is paid for. Empty = never paid.')
    auto_renew = models.BooleanField(default=True, help_text='Off once the handyman cancels.')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.handyman} - {self.get_plan_display()} - {self.state_label}"

    # ---- state
    @staticmethod
    def compute_state(expires_on, auto_renew, has_open_invoice, today=None):
        today = today or timezone.localdate()
        if expires_on is not None and expires_on >= today:
            return ACTIVE if auto_renew else CANCELLING
        if not auto_renew:
            return CANCELLED
        if has_open_invoice:
            return AWAITING
        return LAPSED if expires_on else NEW

    def is_active_on(self, day):
        return self.expires_on is not None and self.expires_on >= day

    @property
    def is_active(self):
        return self.is_active_on(timezone.localdate())

    @property
    def days_left(self):
        """Days until the last paid day (0 = last day is today). None when not active."""
        return (self.expires_on - timezone.localdate()).days if self.is_active else None

    @property
    def open_invoice(self):
        return self.invoices.filter(status='issued').first()

    @property
    def state(self):
        return self.compute_state(self.expires_on, self.auto_renew, self.open_invoice is not None)

    @property
    def state_label(self):
        return STATE_LABELS[self.state]

    @property
    def state_tone(self):
        return STATE_TONES[self.state]

    @property
    def price(self):
        return plan_price(self.plan)

    # ---- who may act
    def _check_actor(self, by):
        """by=None is the system (the daily job). Otherwise an administrator or the handyman themselves."""
        if by is None or getattr(by, 'role', None) == 'admin' or by.pk == self.handyman_id:
            return
        raise ValidationError("You cannot manage this subscription.")

    @classmethod
    def for_handyman(cls, user):
        if getattr(user, 'role', None) != 'handyman':
            raise ValidationError("Only handymen can subscribe.")
        subscription, _ = cls.objects.get_or_create(handyman=user)
        return subscription

    # ---- invoices
    def issue_invoice(self, by=None, due_date=None):
        """Issue the invoice for the next paid period (the current plan)."""
        from .models import DocumentCounter, Invoice, default_payment_instructions
        self._check_actor(by)
        if not self.auto_renew:
            raise ValidationError("This subscription is cancelled. Subscribe again to continue.")
        if self.open_invoice is not None:
            raise ValidationError("An invoice for this subscription is already awaiting payment.")
        if due_date is None:
            due_date = self.expires_on if self.is_active else timezone.localdate() + timedelta(days=first_due_days())
        with transaction.atomic():
            invoice = Invoice(
                invoice_type=Invoice.SUBSCRIPTION, subscription=self, subscription_plan=self.plan,
                total_amount=plan_price(self.plan), reason=f"{self.get_plan_display()} subscription",
                payment_instructions=default_payment_instructions(), due_date=due_date, issued_by=by,
            )
            invoice.number = DocumentCounter.next_number(Invoice.PREFIXES[Invoice.SUBSCRIPTION])
            invoice.save()
        _notify(self, f"invoice:{invoice.number}",
                f"Subscription invoice {invoice.number}",
                f"Your {self.get_plan_display().lower()} HandyConnect subscription invoice {invoice.number} for "
                f"{money(invoice.total_amount)} is ready. Pay by {invoice.due_date:%d/%m/%Y}.\n\n"
                f"{invoice.payment_instructions}")
        return invoice

    def subscribe(self, plan, by=None):
        """Choose a plan. Returns the invoice to pay, or None if the new plan simply starts at the next renewal."""
        self._check_actor(by)
        plan_price(plan)                                    # rejects an unknown plan
        with transaction.atomic():
            if not self.auto_renew:                         # subscribing again after a cancellation
                self.auto_renew, self.cancelled_at = True, None
            invoice = self.open_invoice
            if invoice is not None and invoice.subscription_plan != plan:
                if hasattr(invoice, 'invoice_payment'):
                    raise ValidationError("A payment is already being processed for the open invoice. "
                                          "Ask the administrator to cancel it first.")
                invoice.status = invoice.CANCELLED          # replaced by an invoice for the new plan
                invoice.save(update_fields=['status'])
                invoice = None
            self.plan = plan
            self.save()
            if invoice is not None:
                return invoice
            if self.is_active and self.days_left > invoice_days_before():
                return None                                 # already covered; the plan applies from the next renewal
            return self.issue_invoice(by=by)

    def cancel(self, by=None):
        """Stop renewing. No refund; access continues until expires_on."""
        self._check_actor(by)
        if not self.auto_renew:
            raise ValidationError("This subscription is already cancelled.")
        with transaction.atomic():
            self.auto_renew, self.cancelled_at = False, timezone.now()
            self.save()
            invoice = self.open_invoice
            if invoice is not None:
                invoice.status = invoice.CANCELLED
                invoice.save(update_fields=['status'])

    def activate_after_payment(self, plan=None):
        """Called when a subscription invoice is cleared. Returns (first day, last day) now covered."""
        today = timezone.localdate()
        plan = plan or self.plan
        start = self.expires_on + timedelta(days=1) if self.is_active_on(today) else today
        end = add_months(start, PLAN_MONTHS[plan]) - timedelta(days=1)
        self.expires_on, self.plan = end, plan
        self.save()
        return start, end

    def admin_extend(self, by, days):
        """Free extension by an administrator, for example as a goodwill gesture."""
        if getattr(by, 'role', None) != 'admin':
            raise ValidationError("Only an administrator can extend a subscription.")
        if not 1 <= days <= 366:
            raise ValidationError("Extend by between 1 and 366 days.")
        today = timezone.localdate()
        base = self.expires_on if self.is_active_on(today) else today - timedelta(days=1)
        self.expires_on = base + timedelta(days=days)
        stamp = f"{today:%d/%m/%Y}: extended by {days} days by {by.get_username()} (now valid until {self.expires_on:%d/%m/%Y})."
        self.admin_note = f"{self.admin_note}\n{stamp}".strip()
        self.save()


class SubscriptionReminder(models.Model):
    """A message sent to a handyman. `kind` makes each one go out only once."""

    subscription = models.ForeignKey(HandymanSubscription, on_delete=models.CASCADE, related_name='reminders')
    kind = models.CharField(max_length=80)
    subject = models.CharField(max_length=160)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [models.UniqueConstraint(fields=['subscription', 'kind'], name='one_reminder_per_kind')]

    def __str__(self):
        return f"{self.subscription.handyman}: {self.subject}"


def _notify(subscription, kind, subject, message):
    """Record the message (shown on the handyman's subscription page) and email it. Sent once per kind.

    To also show it in the bell menu, create the project's Notification object here
    (see the `notifications` app) and keep the rest as it is."""
    reminder, created = SubscriptionReminder.objects.get_or_create(
        subscription=subscription, kind=kind, defaults={'subject': subject, 'message': message})
    if created and subscription.handyman.email:
        send_mail(subject, message, None, [subscription.handyman.email], fail_silently=True)
    return created


# ------------------------------------------------------------------ the daily job
def run_daily(today=None):
    """Issue renewal invoices and send reminders. Safe to run more than once a day."""
    today = today or timezone.localdate()
    summary = {'subscriptions_created': 0, 'invoices_issued': 0, 'messages_sent': 0}
    messages_before = SubscriptionReminder.objects.count()
    for user in get_user_model().objects.filter(role='handyman', is_active=True):
        subscription, created = HandymanSubscription.objects.get_or_create(handyman=user)
        summary['subscriptions_created'] += int(created)
        if not subscription.auto_renew:
            continue                                        # cancelled: no more invoices or reminders
        active = subscription.is_active_on(today)
        days_left = (subscription.expires_on - today).days if active else None
        invoice = subscription.open_invoice
        if invoice is None and (not active or days_left <= invoice_days_before()):
            due = subscription.expires_on if active else today + timedelta(days=first_due_days())
            invoice = subscription.issue_invoice(by=None, due_date=due)
            summary['invoices_issued'] += 1
        if invoice is None:
            continue
        pay = f"Invoice {invoice.number}: {money(invoice.total_amount)}, due {invoice.due_date:%d/%m/%Y}. {invoice.payment_instructions}"
        if active and days_left in REMINDER_DAYS:
            when = 'today' if days_left == 0 else f"in {days_left} day{'s' if days_left != 1 else ''}"
            _notify(subscription, f"expiring:{days_left}:{subscription.expires_on}",
                    f"Your HandyConnect subscription ends {when}",
                    f"Your subscription ends {when}. After that you are hidden from search and cannot take new "
                    f"requests, so please renew.\n\n{pay}")
        elif not active and subscription.expires_on:
            _notify(subscription, f"lapsed:{subscription.expires_on}",
                    "Your HandyConnect subscription has lapsed",
                    f"Your subscription ended on {subscription.expires_on:%d/%m/%Y}. You are hidden from search and "
                    f"cannot take new requests until you pay.\n\n{pay}")
    summary['messages_sent'] = SubscriptionReminder.objects.count() - messages_before
    return summary


# ------------------------------------------------------------------ helpers for the rest of the site
def has_active_subscription(user):
    """True for a handyman whose subscription is paid up today."""
    if getattr(user, 'role', None) != 'handyman' or not user.is_authenticated:
        return False
    return HandymanSubscription.objects.filter(handyman=user, expires_on__gte=timezone.localdate()).exists()


def subscribed_handymen():
    """Handymen who may be listed in search and offered new requests."""
    return get_user_model().objects.filter(role='handyman', is_active=True,
                                           subscription__expires_on__gte=timezone.localdate())


def subscription_required(view):
    """For views where a handyman takes on NEW work (accepting a request). Work already accepted is not affected."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if getattr(request.user, 'role', None) == 'handyman' and not has_active_subscription(request.user):
            messages.error(request, 'Your subscription is not active. Subscribe to take new requests.')
            return redirect('payments:my_subscription')
        return view(request, *args, **kwargs)
    return wrapper
