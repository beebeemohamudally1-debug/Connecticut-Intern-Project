
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Invoice, Receipt
from .subscriptions import (ACTIVE, AWAITING, CANCELLING, LAPSED, NEW, STATE_LABELS, STATE_TONES,
                            HandymanSubscription, plan_options, plan_price)
from .views import role_required

User = get_user_model()


def _do(request, action, success=''):
    """Run a subscription action, turning rule errors into messages. Returns the action's result."""
    try:
        result = action()
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return None
    if success:
        messages.success(request, success)
    return result


# ================================================================ administrator
@role_required('admin')
def subscription_list(request):
    handymen = User.objects.filter(role='handyman', is_active=True).order_by('first_name', 'last_name', 'username')
    subscriptions = {s.handyman_id: s for s in HandymanSubscription.objects.all()}
    open_invoices = {i.subscription_id: i for i in Invoice.objects.filter(invoice_type=Invoice.SUBSCRIPTION, status=Invoice.ISSUED)}
    rows, counts = [], {ACTIVE: 0, AWAITING: 0, LAPSED: 0}
    for handyman in handymen:
        sub = subscriptions.get(handyman.pk)
        invoice = open_invoices.get(sub.pk) if sub else None
        state = (HandymanSubscription.compute_state(sub.expires_on, sub.auto_renew, invoice is not None)
                 if sub else NEW)
        key = ACTIVE if state in (ACTIVE, CANCELLING) else state
        if key in counts:
            counts[key] += 1
        rows.append({'handyman': handyman, 'sub': sub, 'invoice': invoice, 'state': state,
                     'label': STATE_LABELS[state], 'tone': STATE_TONES[state],
                     'price': sub.price if sub else plan_price('monthly')})
    return render(request, 'payments/admin_listing_fees.html', {'rows': rows, 'counts': counts})


@role_required('admin')
@require_POST
def subscription_issue_invoice(request, handyman_id):
    handyman = get_object_or_404(User, pk=handyman_id, role='handyman')

    def action():
        return HandymanSubscription.for_handyman(handyman).issue_invoice(by=request.user)
    invoice = _do(request, action)
    if invoice:
        messages.success(request, f'Invoice {invoice.number} issued to {handyman.get_full_name() or handyman.username}.')
    return redirect('payments:subscription_list')


@role_required('admin')
@require_POST
def subscription_extend(request, handyman_id):
    handyman = get_object_or_404(User, pk=handyman_id, role='handyman')
    try:
        days = int(request.POST.get('days', ''))
    except ValueError:
        messages.error(request, 'Enter the number of days.')
        return redirect('payments:subscription_list')

    def action():
        subscription = HandymanSubscription.for_handyman(handyman)
        subscription.admin_extend(request.user, days)
        return subscription
    subscription = _do(request, action)
    if subscription:
        messages.success(request, f'Subscription extended. Valid until {subscription.expires_on:%d/%m/%Y}.')
    return redirect('payments:subscription_list')


# ================================================================ handyman
@role_required('handyman')
def my_subscription(request):
    sub = HandymanSubscription.objects.filter(handyman=request.user).first()
    invoice = sub.open_invoice if sub else None
    receipts = (Receipt.objects.filter(invoice__subscription=sub).select_related('invoice', 'payment')
                if sub else Receipt.objects.none())
    return render(request, 'payments/my_subscription.html', {
        'sub': sub, 'invoice': invoice, 'receipts': receipts,
        'state': sub.state if sub else NEW, 'state_label': sub.state_label if sub else STATE_LABELS[NEW],
        'state_tone': sub.state_tone if sub else STATE_TONES[NEW],
        'plans': plan_options(), 'reminders': sub.reminders.all()[:5] if sub else [],
    })


@role_required('handyman')
@require_POST
def subscription_subscribe(request):
    plan = request.POST.get('plan', '')

    def action():
        return HandymanSubscription.for_handyman(request.user).subscribe(plan, by=request.user)
    try:
        invoice = action()
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        if invoice is not None:
            messages.success(request, f'Invoice {invoice.number} is ready. Pay it as shown below and your subscription '
                                      'starts once the administrator clears the payment.')
        else:
            messages.success(request, 'Saved. You are already covered, and this plan applies from your next renewal.')
    return redirect('payments:my_subscription')


@role_required('handyman')
@require_POST
def subscription_cancel(request):
    sub = HandymanSubscription.objects.filter(handyman=request.user).first()
    if sub is None:
        messages.error(request, 'You have no subscription to cancel.')
    else:
        ends = f' You stay listed until {sub.expires_on:%d/%m/%Y}.' if sub.is_active else ''
        _do(request, lambda: sub.cancel(by=request.user), 'Subscription cancelled. It will not renew.' + ends)
    return redirect('payments:my_subscription')


@role_required('handyman')
def subscription_receipt(request, pk):
    receipt = get_object_or_404(
        Receipt.objects.select_related('invoice', 'invoice__subscription', 'payment'),
        pk=pk, invoice__subscription__handyman=request.user)
    return render(request, 'payments/subscription_receipt.html', {'receipt': receipt, 'invoice': receipt.invoice})
