"""Admin portal - Payment Status: one service request's quotations and material receipts, checked
before the job invoice is issued (FR-A-9 part B: the material quotation is paid at the actual cost,
after the receipts are reviewed). Then it hands over to the payments team's invoice pages.

This view only READS the database (admin only).
  - Receipts: Approve / Reject post to the existing payments:receipt_action view and come back here.
  - Invoice: Issue Invoice opens payments:invoice_issue (only once the checklist is complete), then
    Record payment opens payments:invoice_record_payment, and the receipt number shows once cleared.
BACKEND (payments):
  - No materials: a material request with estimated cost 0 means "no materials needed" (team rule,
    see materials_state). No request yet means the page waits for one.
  - Invoice.issue_job does not check the receipts yet, so the invoice is only held back on this page.
  - There is no action that changes an accepted material quotation to the receipts total, so
    "Send Final Material Quotation" is a demo button.
"""
from decimal import Decimal
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from bookings.models import ServiceRequest
from dashboard.permissions import role_required
from payments.models import Invoice, MaterialPurchaseRequest, MaterialReceipt, Quotation

from .admin_views import _person_name

QUOTE_LABEL = {
    Quotation.DRAFT: 'Draft', Quotation.SENT: 'Awaiting customer', Quotation.REVISION_REQUESTED: 'Changes requested',
    Quotation.REVISED: 'Revised, not sent', Quotation.ACCEPTED: 'Accepted', Quotation.DECLINED: 'Declined',
    Quotation.CANCELLED: 'Cancelled',
}


def _latest(quotes, kind):
    """The newest quotation of this kind that still counts (not cancelled), or None."""
    return next((q for q in quotes if q.quotation_type == kind and q.status != Quotation.CANCELLED), None)


def _money(value):
    return f'MUR {value:,.2f}'


def materials_state(sr):
    """Does this job need materials? Used by Payment Status, Service Quotation Details, Schedule Service
    (through accounts/templatetags/admin_materials.py for the templates).

    Team rule (no backend change): the handyman sends a material request for every job, using the
    existing form. Estimated cost 0 means "no materials needed".
    Returns {'state', 'label', 'note'} (note: one sentence for the customer response pop-up):
      requested -> a real material request is in progress (submitted or forwarded)
      none      -> the latest request has estimated cost 0: the job is labour only
      waiting   -> no request yet, or the last one was rejected
    """
    purchase = (sr.material_requests.order_by('-created_at').first()
                if hasattr(sr, 'material_requests') else None)
    if purchase and purchase.estimated_cost == 0 and purchase.status != MaterialPurchaseRequest.FORWARDED:
        return {'state': 'none', 'label': 'No materials needed',
                'note': 'The handyman says no materials are needed, so the job is labour only.'}
    if purchase and purchase.status != MaterialPurchaseRequest.REJECTED:
        return {'state': 'requested', 'label': 'Material request sent', 'note': ''}
    if purchase:
        return {'state': 'waiting', 'label': 'Material request rejected: waiting for a new one',
                'note': 'The material request was rejected. Payment waits for the handyman\'s new request.'}
    return {'state': 'waiting', 'label': 'Waiting for the handyman\'s material request',
            'note': 'Payment comes after the handyman says which materials are needed (or none).'}


@role_required('admin')
def payment_status(request, request_id):
    sr = get_object_or_404(ServiceRequest.objects.select_related('customer'), pk=request_id)
    quotes = list(sr.quotations.select_related('payment').order_by('-created_at'))
    labour, material = _latest(quotes, Quotation.LABOUR), _latest(quotes, Quotation.MATERIAL)
    purchase = (MaterialPurchaseRequest.objects.filter(request=sr).prefetch_related('receipts')
                .order_by('-created_at').first())
    receipts = list(purchase.receipts.order_by('created_at')) if purchase else []
    approved_total = sum((r.amount_spent for r in receipts if r.status == MaterialReceipt.APPROVED), Decimal('0'))
    waiting = sum(1 for r in receipts if r.status == MaterialReceipt.SUBMITTED)
    mats = materials_state(sr)          # requested / none / waiting (see materials_state)
    materials_used = mats['state'] == 'requested'

    # ---------- Checklist before payment (each: label, detail, ok) ----------
    checks = []
    checks.append(('Service quotation accepted',
                   QUOTE_LABEL.get(labour.status, labour.get_status_display()) if labour else 'Not prepared yet',
                   bool(labour and labour.status == Quotation.ACCEPTED)))
    if mats['state'] != 'requested':
        checks.append(('Materials', mats['label'], mats['state'] == 'none'))
    elif purchase.status == MaterialPurchaseRequest.SUBMITTED:
        checks.append(('Materials', 'Material request waiting for your review', False))
    else:
        material_ok = bool(material and material.status == Quotation.ACCEPTED)
        checks.append(('Material quotation accepted',
                       QUOTE_LABEL.get(material.status, material.get_status_display()) if material else 'Not prepared yet',
                       material_ok))
        if not receipts:
            detail, ok = 'Waiting for the handyman to upload them', False
        elif waiting:
            detail, ok = f'{waiting} waiting for your review', False
        elif not approved_total:
            detail, ok = 'No receipt approved', False
        else:
            detail, ok = f'Approved: {_money(approved_total)}', True
        checks.append(('Receipts approved', detail, ok))
        same = bool(material and ok and material.total_amount == approved_total)
        if material and ok and not same:
            detail = f'Quoted {_money(material.total_amount)}, receipts {_money(approved_total)}'
        else:
            detail = 'Matches the approved receipts' if same else 'After the receipts are approved'
        checks.append(('Material quotation at the actual cost', detail, same))
    ready = all(ok for _, _, ok in checks)

    # ---------- Quotations and payments ----------
    rows, owed, paid = [], Decimal('0'), Decimal('0')
    for q, title in ((labour, 'Service quotation'), (material if materials_used else None, 'Material quotation')):
        if not q:
            continue
        accepted = q.status == Quotation.ACCEPTED
        if accepted:
            owed += q.total_amount
            if q.is_paid:
                paid += q.payment.amount
        rows.append({
            'title': title, 'ref': f'Q-{q.pk}', 'amount': _money(q.total_amount),
            'status': 'Paid' if q.is_paid else QUOTE_LABEL.get(q.status, q.get_status_display()),
            'tone': 'paid' if q.is_paid else ('ok' if accepted else 'wait'),
            'paid_on': (f'{q.payment.date_received:%d %b %Y} · {q.payment.get_method_display()}' if q.is_paid else ''),
            'url': reverse('payments:quotation_detail_admin', args=[q.pk]),
        })
    all_paid = bool(rows) and all(r['status'] == 'Paid' for r in rows)

    # ---------- Job invoice (payments team's pages) ----------
    invoice = (Invoice.objects.filter(request=sr, invoice_type=Invoice.JOB)
               .exclude(status=Invoice.CANCELLED).select_related('invoice_payment', 'receipt').first())
    # The invoice pages come back here after issuing or recording (?next=, payments.views._back)
    back = '?' + urlencode({'next': request.path})
    inv = None
    if invoice:
        saved = getattr(invoice, 'invoice_payment', None)
        receipt = getattr(invoice, 'receipt', None) if invoice.status == Invoice.PAID else None
        inv = {
            'number': invoice.number, 'total': _money(invoice.total_amount), 'status': invoice.get_status_display(),
            'tone': 'paid' if invoice.status == Invoice.PAID else ('late' if invoice.is_overdue else 'wait'),
            'due': f'{invoice.due_date:%d %b %Y}', 'overdue': invoice.is_overdue,
            'saved': (f'{_money(saved.amount)} saved, not cleared' if saved and saved.status != saved.CLEARED else ''),
            'receipt': receipt.number if receipt else '',
            # View Receipt pop-up (the payments team's receipt page is for customers only)
            'receipt_info': ({
                'number': receipt.number, 'issued': f'{receipt.issued_at:%d %b %Y}',
                'amount': _money(receipt.payment.amount), 'received': f'{receipt.payment.date_received:%d %b %Y}',
                'method': receipt.payment.get_method_display(), 'reference': receipt.payment.reference or '-',
                'by': receipt.payment.recorded_by.get_full_name() or receipt.payment.recorded_by.username,
            } if receipt else None),
            'pay_url': (reverse('payments:invoice_record_payment', args=[invoice.pk]) + back
                        if invoice.status == Invoice.ISSUED else ''),
        }

    page = {
        'request_id': sr.pk, 'reference': sr.reference, 'customer': _person_name(sr.customer),
        'service': sr.service_category or 'Service request',
        'checks': [{'label': l, 'detail': d, 'ok': ok} for l, d, ok in checks],
        'ready': ready, 'rows': rows, 'all_paid': all_paid,
        'owed': _money(owed), 'paid': _money(paid), 'left': _money(owed - paid),
        'purchase': purchase,
        'receipts': [{
            'id': r.pk, 'amount': _money(r.amount_spent), 'status': r.status, 'label': r.get_status_display(),
            'date': f'{r.created_at:%d %b %Y}', 'image': r.image.url if r.image else '', 'note': r.admin_note,
        } for r in receipts],
        'approved_total': _money(approved_total),
        'material_total': _money(material.total_amount) if material and materials_used else '',
        'difference': (_money(material.total_amount - approved_total)
                       if material and materials_used and receipts and not waiting else ''),
        'can_update': bool(material and material.status == Quotation.ACCEPTED and not material.is_paid
                           and receipts and not waiting and approved_total and material.total_amount != approved_total),
        'schedule_url': (reverse('accounts_admin:appointment_schedule', args=['service']) + f'?request={sr.pk}'
                         if all_paid else ''),
        'invoice': inv,
        # Issue Invoice only once everything is checked and nothing is paid yet
        'issue_url': (reverse('payments:invoice_issue', args=[sr.pk]) + back
                      if ready and not inv and rows and not any(r['status'] == 'Paid' for r in rows) else ''),
        'invoices_url': reverse('payments:invoice_list'),
    }
    return render(request, 'payments/admin_payment_status.html', {'page': page})
