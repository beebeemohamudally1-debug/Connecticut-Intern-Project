"""Pages for handyman payouts: the administrator's list and record form, and the handyman's earnings."""
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from jobs.models import Job

from .payouts import (HandymanPayout, handyman_earnings, jobs_ready_for_payout, jobs_waiting_for_customer_payment,
                      suggested_amounts)

ADMIN_BASE, HANDYMAN_BASE = 'base_admin.html', 'jobs/base_user.html'


def _role(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if getattr(request.user, 'role', None) not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


class PayoutForm(forms.Form):
    labour_amount = forms.DecimalField(label='Labour (MUR)', min_value=0, decimal_places=2, max_digits=10)
    materials_amount = forms.DecimalField(label='Materials (MUR)', min_value=0, decimal_places=2, max_digits=10, initial=0)
    date_paid = forms.DateField(label='Date paid', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    method = forms.ChoiceField(label='Payment method', choices=HandymanPayout.METHOD_CHOICES)
    reference = forms.CharField(label='Reference number (optional)', required=False, max_length=60)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'in'


# ================================================================== administrator
@_role('admin')
def payout_list(request):
    ready = []
    for job in jobs_ready_for_payout():
        labour, materials = suggested_amounts(job)
        ready.append({'job': job, 'labour': labour, 'materials': materials})
    payouts = HandymanPayout.objects.select_related('job', 'handyman', 'invoice')
    status = request.GET.get('status')
    if status in (HandymanPayout.PAID, HandymanPayout.CONFIRMED):
        payouts = payouts.filter(status=status)
    return render(request, 'payments/admin_payouts.html', {
        'ready': ready, 'waiting': jobs_waiting_for_customer_payment(), 'payouts': payouts, 'status': status,
    })


@_role('admin')
def payout_record(request, job_id):
    job = get_object_or_404(Job.objects.select_related('handyman', 'customer'), pk=job_id)
    invoice, problem = HandymanPayout.blocker(job)
    if problem:
        messages.error(request, problem)
        return redirect('payments:payout_list')
    labour, materials = suggested_amounts(job)
    form = PayoutForm(request.POST or None, initial={
        'labour_amount': labour, 'materials_amount': materials, 'date_paid': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        try:
            payout = HandymanPayout.record(request.user, job, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
        else:
            messages.success(request, f'Payout {payout.number} recorded.')
            return redirect('payments:payout_detail', pk=payout.pk)
    hint = (f"Customer paid MUR {invoice.total_amount} (invoice {invoice.number}). "
            f"Suggested: labour {'MUR ' + str(labour) if labour is not None else 'not known, enter it'}, "
            f"materials MUR {materials} from approved receipts.")
    return render(request, 'payments/form_page.html', {
        'form': form, 'title': 'Record handyman payout', 'subtitle': f'{job.reference} · {job.service_name} · {job.handyman}',
        'base_template': ADMIN_BASE, 'nav_page': 'payouts', 'button': 'Record payout', 'back_url': 'payments:payout_list', 'extra': hint,
    })


# ================================================================== administrator and handyman
@_role('admin', 'handyman')
def payout_detail(request, pk):
    payout = get_object_or_404(HandymanPayout.objects.select_related('job', 'handyman', 'invoice', 'recorded_by'), pk=pk)
    is_admin = request.user.role == 'admin'
    if not is_admin and payout.handyman_id != request.user.pk:
        raise Http404                                           # not yours
    return render(request, 'payments/payout_detail.html', {
        'payout': payout, 'is_admin': is_admin, 'role': request.user.role,
        'base_template': ADMIN_BASE if is_admin else HANDYMAN_BASE,
        'notes': payout.cross_check if is_admin else [],
    })


# ================================================================== handyman
@_role('handyman')
def my_earnings(request):
    return render(request, 'payments/handyman_earnings.html', {
        'role': 'handyman',
        'earnings': handyman_earnings(request.user),
        'payouts': HandymanPayout.objects.filter(handyman=request.user).select_related('job'),
        'ready': jobs_ready_for_payout().filter(handyman=request.user),
        'waiting': jobs_waiting_for_customer_payment().filter(handyman=request.user),
    })


@_role('handyman')
@require_POST
def payout_confirm(request, pk):
    payout = get_object_or_404(HandymanPayout, pk=pk, handyman=request.user)
    try:
        payout.confirm(request.user, request.FILES.get('proof_image'))
        messages.success(request, 'Thank you. You confirmed that you received this payout.')
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    return redirect('payments:payout_detail', pk=pk)
