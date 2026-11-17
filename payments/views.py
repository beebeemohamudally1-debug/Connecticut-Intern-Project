from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from bookings.models import ServiceRequest, ServiceRequestAssignment

from .forms import (LabourEstimateForm, MaterialReceiptForm, MaterialRequestForm, NoteForm, PaymentForm,
                    QuotationForm)
from .models import (LabourEstimate, MaterialPurchaseRequest, MaterialReceipt, Payment, Quotation)


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


def _run(request, action, success):
    """Run a model action, turning rule errors into messages."""
    try:
        action()
        messages.success(request, success)
        return True
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return False


def _form_page(request, form, *, title, subtitle='', base, nav, button='Save', back='', extra=''):
    return render(request, 'payments/form_page.html', {
        'form': form, 'title': title, 'subtitle': subtitle, 'base_template': base,
        'nav_page': nav, 'button': button, 'back_url': back, 'extra': extra,
    })


def _handyman_has_accepted(user, service_request):
    return ServiceRequestAssignment.objects.filter(
        service_request=service_request, handyman=user, status='accepted').exists()


# ============================================================ admin: labour estimates
@role_required('admin')
def estimate_list(request):
    estimates = LabourEstimate.objects.select_related('request', 'handyman')
    return render(request, 'payments/estimate_list.html', {'estimates': estimates})


@role_required('admin')
@require_POST
def estimate_action(request, pk):
    estimate = get_object_or_404(LabourEstimate, pk=pk)
    action, note = request.POST.get('action'), request.POST.get('note', '')
    if action == 'approve':
        _run(request, lambda: estimate.approve(request.user), 'Estimate approved.')
    elif action == 'reject':
        _run(request, lambda: estimate.reject(request.user, note), 'Estimate rejected.')
    elif action == 'revision':
        _run(request, lambda: estimate.request_revision(request.user, note), 'Revision requested from the handyman.')
    return redirect('payments:estimate_list')


# ================================================================ admin: quotations
@role_required('admin')
def quotation_list(request):
    quotations = Quotation.objects.select_related('request', 'request__customer').order_by('-created_at')
    return render(request, 'payments/quotation_list.html', {'quotations': quotations})


@role_required('admin')
def quotation_detail_admin(request, pk):
    quotation = get_object_or_404(Quotation.objects.select_related('request', 'request__customer', 'labour_estimate'), pk=pk)
    return render(request, 'payments/quotation_admin_detail.html', {'quotation': quotation})


@role_required('admin')
def quotation_create(request, request_id):
    service_request = get_object_or_404(ServiceRequest, pk=request_id)
    estimate = LabourEstimate.objects.filter(pk=request.GET.get('estimate'), request=service_request,
                                             status=LabourEstimate.APPROVED).first()
    initial = {'total_amount': estimate.amount, 'work_description': estimate.breakdown} if estimate else None
    form = QuotationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        quotation = form.save(commit=False)
        quotation.request = service_request
        quotation.created_by = request.user
        quotation.labour_estimate = estimate
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
    return render(request, 'payments/quotation_form.html', {'form': form, 'service_request': service_request, 'estimate': estimate})


@role_required('admin')
def quotation_edit(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    editable = (Quotation.DRAFT, Quotation.REVISED, Quotation.REVISION_REQUESTED)
    if quotation.status not in editable:
        messages.error(request, 'This quotation can no longer be edited.')
        return redirect('payments:quotation_detail_admin', pk=pk)
    form = QuotationForm(request.POST or None, instance=Quotation.objects.get(pk=pk))
    if request.method == 'POST' and form.is_valid():
        total, text = form.cleaned_data['total_amount'], form.cleaned_data['work_description']
        revising = quotation.status == Quotation.REVISION_REQUESTED
        action = (lambda: quotation.revise(request.user, total, text)) if revising else (lambda: quotation.update(total, text))
        if 'send' in request.POST:   # Send to Customer: save, then send it in one step
            action_then_send = action
            action = lambda: (action_then_send(), quotation.send())
            done = 'Quotation sent to the customer.'
        else:
            done = 'Quotation revised. Send it to re-issue it.' if revising else 'Quotation updated.'
        if _run(request, action, done):
            return redirect('payments:quotation_detail_admin', pk=pk)
    # Admin layout for Edit / Revise (the shared form_page.html stays for the handyman forms)
    return render(request, 'payments/quotation_edit.html', {'form': form, 'quotation': quotation})


@role_required('admin')
@require_POST
def quotation_send(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    _run(request, quotation.send, 'Quotation sent to the customer.')
    return redirect(request.POST.get('next') or 'payments:quotation_list')


@role_required('admin')
@require_POST
def quotation_cancel(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    _run(request, lambda: quotation.cancel(request.user), 'Quotation cancelled.')
    return redirect('payments:quotation_detail_admin', pk=pk)


@role_required('admin')
def payment_record(request, quotation_id):
    quotation = get_object_or_404(Quotation, pk=quotation_id)
    if not quotation.ready_for_payment:
        messages.error(request, quotation.readiness_issue)
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


# ============================================================== admin: materials
@role_required('admin')
def admin_materials(request):
    purchase_requests = MaterialPurchaseRequest.objects.select_related('request', 'handyman', 'quotation')
    receipts = MaterialReceipt.objects.select_related('purchase_request', 'purchase_request__request', 'uploaded_by')
    return render(request, 'payments/admin_materials.html', {'purchase_requests': purchase_requests, 'receipts': receipts})


@role_required('admin')
@require_POST
def material_request_action(request, pk):
    purchase = get_object_or_404(MaterialPurchaseRequest, pk=pk)
    action, note = request.POST.get('action'), request.POST.get('note', '')
    if action == 'forward':
        total = request.POST.get('total') or None
        _run(request, lambda: purchase.forward(request.user, total), 'Material quotation sent to the customer.')
    elif action == 'reject':
        _run(request, lambda: purchase.reject(request.user, note), 'Purchase request rejected.')
    return redirect('payments:admin_materials')


@role_required('admin')
@require_POST
def receipt_action(request, pk):
    receipt = get_object_or_404(MaterialReceipt, pk=pk)
    action, note = request.POST.get('action'), request.POST.get('note', '')
    if action == 'approve':
        _run(request, lambda: receipt.approve(request.user), 'Receipt approved.')
    elif action == 'reject':
        _run(request, lambda: receipt.reject(request.user, note), 'Receipt rejected.')
    return redirect('payments:admin_materials')


# ================================================================= handyman
@role_required('handyman')
def my_estimates(request):
    estimates = LabourEstimate.objects.filter(handyman=request.user).select_related('request')
    return render(request, 'payments/my_estimates.html', {'estimates': estimates})


@role_required('handyman')
def estimate_submit(request, request_id):
    service_request = get_object_or_404(ServiceRequest, pk=request_id)
    if not _handyman_has_accepted(request.user, service_request):
        raise PermissionDenied
    form = LabourEstimateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        estimate = form.save(commit=False)
        estimate.request, estimate.handyman = service_request, request.user
        estimate.save()
        messages.success(request, 'Estimate sent to the administrator.')
        return redirect('payments:my_estimates')
    return _form_page(request, form, title='Labour estimate', subtitle=f'Request {service_request.reference}',
                      base='base_handyman.html', nav='requests', button='Send estimate', back='payments:my_estimates')


@role_required('handyman')
def estimate_resubmit(request, pk):
    estimate = get_object_or_404(LabourEstimate, pk=pk, handyman=request.user)
    form = LabourEstimateForm(request.POST or None, instance=LabourEstimate.objects.get(pk=pk))
    if request.method == 'POST' and form.is_valid():
        if _run(request, lambda: estimate.resubmit(request.user, form.cleaned_data['amount'], form.cleaned_data['breakdown']),
                'Revised estimate sent.'):
            return redirect('payments:my_estimates')
    extra = f"Administrator's note: {estimate.admin_note}" if estimate.admin_note else ''
    return _form_page(request, form, title='Revise estimate', subtitle=f'Request {estimate.request.reference}',
                      base='base_handyman.html', nav='requests', button='Send revised estimate', back='payments:my_estimates', extra=extra)


@role_required('handyman')
def my_materials(request):
    purchases = (MaterialPurchaseRequest.objects.filter(handyman=request.user)
                 .select_related('request', 'quotation').prefetch_related('receipts'))
    return render(request, 'payments/my_materials.html', {'purchases': purchases})


@role_required('handyman')
def material_request_submit(request, request_id):
    service_request = get_object_or_404(ServiceRequest, pk=request_id)
    if not _handyman_has_accepted(request.user, service_request):
        raise PermissionDenied
    form = MaterialRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        purchase = form.save(commit=False)
        purchase.request, purchase.handyman = service_request, request.user
        purchase.save()
        messages.success(request, 'Purchase request sent to the administrator.')
        return redirect('payments:my_materials')
    return _form_page(request, form, title='Material purchase request', subtitle=f'Request {service_request.reference}',
                      base='base_handyman.html', nav='materials', button='Send request', back='payments:my_materials')


@role_required('handyman')
def receipt_upload(request, pk):
    purchase = get_object_or_404(MaterialPurchaseRequest, pk=pk, handyman=request.user)
    form = MaterialReceiptForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        receipt = form.save(commit=False)
        receipt.purchase_request, receipt.uploaded_by = purchase, request.user
        try:
            receipt.full_clean()
            receipt.save()
        except ValidationError as error:
            _form_error(form, error)
        else:
            messages.success(request, 'Receipt uploaded for review.')
            return redirect('payments:my_materials')
    return _form_page(request, form, title='Upload receipt', subtitle=f'Request {purchase.request.reference}',
                      base='base_handyman.html', nav='materials', button='Upload receipt', back='payments:my_materials')


# ================================================================== customer
@role_required('customer')
def my_quotations(request):
    quotations = (Quotation.objects.filter(request__customer=request.user)
                  .exclude(status=Quotation.DRAFT).select_related('request').order_by('-created_at'))
    return render(request, 'payments/my_quotations.html', {'quotations': quotations})


@role_required('customer')
def quotation_detail(request, pk):
    quotation = get_object_or_404(Quotation.objects.exclude(status=Quotation.DRAFT), pk=pk, request__customer=request.user)
    if request.method == 'POST':
        if 'accept' in request.POST:
            _run(request, lambda: quotation.accept(request.user), 'You accepted the quotation.')
        elif 'decline' in request.POST:
            _run(request, lambda: quotation.decline(request.user), 'You declined the quotation.')
        elif 'revision' in request.POST:
            _run(request, lambda: quotation.request_revision(request.user, request.POST.get('note', '')), 'Revision requested.')
        return redirect('payments:quotation_detail', pk=pk)
    return render(request, 'payments/quotation_detail.html', {'quotation': quotation})


@role_required('customer')
def payment_history(request):
    payments = (Payment.objects.filter(quotation__request__customer=request.user)
                .select_related('quotation', 'quotation__request').order_by('-date_received'))
    return render(request, 'payments/payment_history.html', {'payments': payments})
