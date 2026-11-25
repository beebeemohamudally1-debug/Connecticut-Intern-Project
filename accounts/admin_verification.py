import os

from django.core.mail import send_mail
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.permissions import role_required

from .admin_views import _local_date, _person_name
from .models import HandymanProfile, ProviderDocument

TEMPLATE = 'accounts/admin_handyman_verify.html'
LABELS = {
    HandymanProfile.STATUS_PENDING: 'Pending',
    HandymanProfile.STATUS_ACTIVE: 'Approved',
    HandymanProfile.STATUS_REJECTED: 'Rejected',
}


def _profile_of(pk):
    """The application of the handyman with this user id (404 when there is none)."""
    return get_object_or_404(HandymanProfile.objects.select_related('user'),
                             user__pk=pk, user__role='handyman')


def _documents(profile):
    documents, certificates = [], 0
    for d in profile.documents.order_by('-kind', 'uploaded_at', 'pk'):   # the ID photo first
        if d.kind == ProviderDocument.KIND_ID:
            title = 'ID card photo'
        else:
            certificates += 1
            title = f'Certificate {certificates}'
        documents.append({
            'title': title, 'file': d.original_name, 'action': 'View image',
            'url': reverse('accounts_admin:handyman_document_file', args=[d.pk]),
        })
    return documents


def _applicant(profile, error=''):
    user = profile.user
    return {
        'id': f'USR-{user.pk:04d}', 'name': _person_name(user), 'email': user.email or '-',
        'submitted': _local_date(profile.created_at), 'status': LABELS[profile.status],
        'decided': _local_date(profile.decided_at),
        'notes': profile.decision_notes or profile.rejection_reason,
        'documents': _documents(profile),
        'decide_url': reverse('accounts_admin:handyman_decide', args=[user.pk]),
        'error': error,
    }


@role_required('admin')
def handyman_verify(request, pk):
    """Registration Verification: one handyman's documents and, while pending, the decision form."""
    return render(request, TEMPLATE, {'applicant': _applicant(_profile_of(pk))})


def _notify(profile, approved, notes):
    if approved:
        subject = 'Your HandyConnect registration was approved'
        body = 'Your registration was approved. You can now log in.'
    else:
        subject = 'Your HandyConnect registration was not approved'
        body = 'Your registration was not approved. Reason: ' + notes
    try:
        send_mail(subject, body, None, [profile.user.email])
    except Exception:
        pass


@role_required('admin')
@require_POST
def handyman_decide(request, pk):
    profile = _profile_of(pk)
    if profile.status != HandymanProfile.STATUS_PENDING:      # a decision is final
        return redirect('accounts_admin:handyman_verify', pk=pk)
    decision = request.POST.get('decision')
    notes = request.POST.get('notes', '').strip()[:1000]
    if decision not in ('approve', 'reject'):
        return redirect('accounts_admin:handyman_verify', pk=pk)
    if decision == 'reject' and not notes:
        return render(request, TEMPLATE, {'applicant': _applicant(
            profile, error='Write the reason for rejecting this registration.')})
    approved = decision == 'approve'
    profile.status = HandymanProfile.STATUS_ACTIVE if approved else HandymanProfile.STATUS_REJECTED
    profile.rejection_reason = '' if approved else notes
    profile.decision_notes = notes
    profile.decided_at = timezone.now()
    profile.decided_by = request.user
    profile.save()
    _notify(profile, approved, notes)
    return redirect('accounts_admin:handyman_verify', pk=pk)


@role_required('admin')
def handyman_document_file(request, doc_pk):
    """An uploaded ID or certificate. Administrators only: the files are never served publicly."""
    document = get_object_or_404(ProviderDocument, pk=doc_pk)
    try:
        response = FileResponse(document.file.open('rb'), as_attachment=False,
                                filename=os.path.basename(document.file.name))
    except (FileNotFoundError, ValueError):
        raise Http404
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response