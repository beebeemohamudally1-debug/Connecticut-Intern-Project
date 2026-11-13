from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from bookings.models import ServiceRequest

from .forms import PaymentForm, QuotationForm
from .models import Payment, Quotation


def role_required(role):
    """Allow only logged-in users whose `role` matches."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if getattr(request.user, 'role', None) != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def _form_error(form, error):
    form.add_error(None, ' '.join(error.messages))


# ---------------------------------------------------------------- admin
@role_required('admin')
def quotation_list(request):
    quotations = Quotation.objects.select_related('request', 'request__customer').order_by('-created_at')
    return render(request, 'payments/quotation_list.html', {'quotations': quotations})


@role_required('admin')
def quotation_create(request, request_id):
    service_request = get_object_or_404(ServiceRequest, pk=request_id)
    form = QuotationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        quotation = form.save(commit=False)
        quotation.request = service_request
        quotation.created_by = request.user
        try:
            quotation.full_clean()
            quotation.save()
            if 'send' in request.POST:
                quotation.send()
        except ValidationError as error:
            _form_error(form, error)
        else:
            messages.success(request, 'Quotation sent to the customer.' if 'send' in request.POST else 'Quotation saved as a draft.')
            return redirect('payments:quotation_list')
    return render(request, 'payments/quotation_form.html', {'form': form, 'service_request': service_request})


@role_required('admin')
@require_POST
def quotation_send(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    try:
        quotation.send()
        messages.success(request, 'Quotation sent to the customer.')
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    return redirect('payments:quotation_list')


@role_required('admin')
def payment_record(request, quotation_id):
    quotation = get_object_or_404(Quotation, pk=quotation_id)
    if quotation.is_paid:
        messages.error(request, 'This quotation has already been paid in full.')
        return redirect('payments:quotation_list')
    form = PaymentForm(request.POST or None, initial={'amount': quotation.total_amount, 'date_received': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        payment = form.save(commit=False)
        payment.quotation = quotation
        payment.recorded_by = request.user
        try:
            payment.save()          # applies every payment rule
        except ValidationError as error:
            _form_error(form, error)
        else:
            messages.success(request, 'Payment recorded.')
            return redirect('payments:quotation_list')
    return render(request, 'payments/payment_form.html', {'form': form, 'quotation': quotation})


# ------------------------------------------------------------- customer
@role_required('customer')
def my_quotations(request):
    quotations = (Quotation.objects.filter(request__customer=request.user)
                  .exclude(status=Quotation.DRAFT).select_related('request').order_by('-created_at'))
    return render(request, 'payments/my_quotations.html', {'quotations': quotations})


@role_required('customer')
def quotation_detail(request, pk):
    quotation = get_object_or_404(Quotation.objects.exclude(status=Quotation.DRAFT), pk=pk, request__customer=request.user)
    if request.method == 'POST':
        try:
            if 'accept' in request.POST:
                quotation.accept(request.user)
                messages.success(request, 'You accepted the quotation.')
            elif 'decline' in request.POST:
                quotation.decline(request.user)
                messages.success(request, 'You declined the quotation.')
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        return redirect('payments:quotation_detail', pk=pk)
    return render(request, 'payments/quotation_detail.html', {'quotation': quotation})


@role_required('customer')
def payment_history(request):
    payments = (Payment.objects.filter(quotation__request__customer=request.user)
                .select_related('quotation', 'quotation__request').order_by('-date_received'))
    return render(request, 'payments/payment_history.html', {'payments': payments})
