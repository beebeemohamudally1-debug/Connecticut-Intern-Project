from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from jobs.permissions import base_template_for, get_role, role_required
from jobs.views import jobs_for
from .forms import ComplaintForm, EnquiryForm, ReplyForm, ResolutionForm
from .models import Complaint, ComplaintEvidence, ComplaintLog, ComplaintMessage
from .signals import (complaint_enquiry_sent, complaint_response_received,
                      complaint_status_changed, complaint_submitted)

ALL_ROLES = ('admin', 'handyman', 'customer')


def complaints_for(user):
    """Admin: all complaints. Others: ones they submitted or that name them."""
    qs = Complaint.objects.select_related('submitted_by', 'against', 'job')
    if get_role(user) == 'admin':
        return qs
    return qs.filter(Q(submitted_by=user) | Q(against=user))


def _errors(form):
    return '; '.join(e for errs in form.errors.values() for e in errs)


@role_required(*ALL_ROLES)
def complaint_list(request):
    role = get_role(request.user)
    items = complaints_for(request.user)
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    by = request.GET.get('by', '')
    if status in dict(Complaint.STATUS_CHOICES):
        items = items.filter(status=status)
    if q:
        items = items.filter(
            Q(reference__icontains=q) | Q(subject__icontains=q) | Q(job__reference__icontains=q) |
            Q(submitted_by__username__icontains=q) | Q(against__username__icontains=q))
    if role == 'admin' and by in ('customer', 'handyman'):
        items = items.filter(submitted_by__role=by)
    return render(request, 'complaints/complaint_list.html', {
        'base_template': base_template_for(request.user), 'role': role,
        'complaints': items, 'status_choices': Complaint.STATUS_CHOICES, 'f': request.GET,
        'user_id': request.user.pk,
    })


@role_required('customer', 'handyman')
def complaint_create(request):
    jobs = jobs_for(request.user)
    form = ComplaintForm(request.POST or None, request.FILES or None, user=request.user, jobs=jobs)
    initial_job = request.GET.get('job')
    if request.method == 'GET' and initial_job and initial_job.isdigit():
        form.initial['job'] = int(initial_job)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            c = form.save(commit=False)
            c.submitted_by = request.user
            c.against = c.job.handyman if get_role(request.user) == 'customer' else c.job.customer
            c.save()
            ComplaintLog.objects.create(
                complaint=c, actor=request.user, to_status=Complaint.PENDING, note='Complaint submitted')
            if form.cleaned_data.get('evidence'):
                ComplaintEvidence.objects.create(
                    complaint=c, uploaded_by=request.user, file=form.cleaned_data['evidence'])
        complaint_submitted.send(sender=Complaint, complaint=c)
        messages.success(request, f'Complaint {c.reference} submitted.')
        return redirect('complaints:detail', pk=c.pk)
    return render(request, 'complaints/complaint_form.html', {
        'base_template': base_template_for(request.user), 'form': form})


def _visible_messages(complaint, user, role):
    msgs = complaint.messages.select_related('author', 'recipient')
    if role == 'admin':
        return msgs
    # A party sees only their own responses and enquiries addressed to them,
    # never the other party's explanation.
    return msgs.filter(Q(author=user) | Q(recipient=user))


@role_required(*ALL_ROLES)
def complaint_detail(request, pk):
    complaint = get_object_or_404(complaints_for(request.user), pk=pk)
    role = get_role(request.user)
    ctx = {
        'base_template': base_template_for(request.user), 'role': role, 'c': complaint,
        'thread': _visible_messages(complaint, request.user, role),
        'log': complaint.log.select_related('actor'),
        'evidence': complaint.evidence.select_related('uploaded_by') if role == 'admin'
        else complaint.evidence.filter(uploaded_by=request.user),
    }
    if role == 'admin':
        if not complaint.is_resolved:
            ctx['enquiry_form'] = EnquiryForm(complaint=complaint)
            ctx['resolution_form'] = ResolutionForm(initial={'status': complaint.status})
    elif not complaint.is_resolved:
        ctx['reply_form'] = ReplyForm()
    return render(request, 'complaints/complaint_detail.html', ctx)


@require_POST
@role_required('customer', 'handyman')
def complaint_reply(request, pk):
    complaint = get_object_or_404(complaints_for(request.user), pk=pk)
    if complaint.is_resolved:
        messages.error(request, 'This complaint is resolved and can no longer be changed.')
        return redirect('complaints:detail', pk=pk)
    form = ReplyForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, _errors(form))
        return redirect('complaints:detail', pk=pk)
    with transaction.atomic():
        msg = ComplaintMessage.objects.create(
            complaint=complaint, author=request.user,
            kind=ComplaintMessage.RESPONSE, body=form.cleaned_data['body'])
        if form.cleaned_data.get('evidence'):
            ComplaintEvidence.objects.create(
                complaint=complaint, uploaded_by=request.user, file=form.cleaned_data['evidence'])
    complaint_response_received.send(sender=Complaint, complaint=complaint, message=msg)
    messages.success(request, 'Your response was sent to the administrator.')
    return redirect('complaints:detail', pk=pk)


@require_POST
@role_required('admin')
def complaint_enquiry(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if complaint.is_resolved:
        messages.error(request, 'This complaint is resolved and can no longer be changed.')
        return redirect('complaints:detail', pk=pk)
    form = EnquiryForm(request.POST, complaint=complaint)
    if not form.is_valid():
        messages.error(request, _errors(form))
        return redirect('complaints:detail', pk=pk)
    with transaction.atomic():
        msg = ComplaintMessage.objects.create(
            complaint=complaint, author=request.user, recipient=form.cleaned_data['recipient'],
            kind=ComplaintMessage.ENQUIRY, body=form.cleaned_data['body'])
        if complaint.status == Complaint.PENDING:
            complaint.status = Complaint.IN_PROGRESS
            complaint.save(update_fields=['status', 'updated_at'])
            ComplaintLog.objects.create(
                complaint=complaint, actor=request.user, from_status=Complaint.PENDING,
                to_status=Complaint.IN_PROGRESS, note='Enquiry sent')
    complaint_enquiry_sent.send(sender=Complaint, complaint=complaint, message=msg)
    messages.success(request, 'Enquiry sent.')
    return redirect('complaints:detail', pk=pk)


@require_POST
@role_required('admin')
def complaint_resolution(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if complaint.is_resolved:
        messages.error(request, 'This complaint is resolved and can no longer be changed.')
        return redirect('complaints:detail', pk=pk)
    form = ResolutionForm(request.POST)
    if not form.is_valid():
        messages.error(request, _errors(form))
        return redirect('complaints:detail', pk=pk)
    old = complaint.status
    new = form.cleaned_data['status']
    outcome = form.cleaned_data['outcome'].strip()
    with transaction.atomic():
        complaint.status = new
        if outcome:
            complaint.outcome = outcome
        if new == Complaint.RESOLVED:
            complaint.resolved_by, complaint.resolved_at = request.user, timezone.now()
        complaint.save()
        ComplaintLog.objects.create(
            complaint=complaint, actor=request.user, from_status=old, to_status=new,
            note='Outcome recorded' if outcome else '')
    if new != old:
        complaint_status_changed.send(sender=Complaint, complaint=complaint)
    messages.success(request, 'Complaint updated.')
    return redirect('complaints:detail', pk=pk)


@role_required(*ALL_ROLES)
def evidence_file(request, pk):
    """Evidence is visible to admins and to the person who uploaded it."""
    ev = get_object_or_404(ComplaintEvidence.objects.filter(
        complaint__in=complaints_for(request.user)), pk=pk)
    if get_role(request.user) != 'admin' and ev.uploaded_by_id != request.user.pk:
        raise Http404
    return FileResponse(ev.file.open('rb'))
