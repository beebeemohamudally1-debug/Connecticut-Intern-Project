"""Admin portal - Manage Services."""

from django.db.models import Count
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from .admin_service_forms import ServiceForm
from django.views.decorators.http import require_POST
from bookings.models import HandymanProfileRequest
from dashboard.permissions import role_required
from services.models import Service, ServiceCategory
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import HandymanProfile
from .admin_views import _person_name, _initials, _account_status

@role_required('admin')
def manage_services(request):
    """Display real services, categories and handyman counts."""

    services = (
        Service.objects
        .select_related('category')
        .annotate(handymen_count=Count('handymen', distinct=True))
        .order_by('category__name', 'name')
    )

    categories = ServiceCategory.objects.order_by('name')

    pending_requests = HandymanProfileRequest.objects.filter(
        request_type=HandymanProfileRequest.TYPE_SERVICE,
        status=HandymanProfileRequest.STATUS_PENDING,
    ).count()

    context = {
        'services': services,
        'categories': categories,
        'pending_requests': pending_requests,
    }

    return render(
        request,
        'services/manage_services.html',
        context,
    )

@role_required('admin')
def view_service(request, service_id):
    """Display the selected service and associated handymen."""

    service = get_object_or_404(
        Service.objects.select_related('category'),
        pk=service_id,
    )

    handymen = (
        service.handymen
        .select_related('user', 'user__region')
        .prefetch_related('service_areas')
        .order_by('user__first_name', 'user__last_name')
    )

    context = {
        'service': service,
        'handymen': handymen,
        'handymen_count': handymen.count(),
    }

    return render(
        request,
        'services/view_service.html',
        context,
    )

@role_required('admin')
def add_service(request):
    """Create a new service."""

    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)

        if form.is_valid():
            service = form.save()

            messages.success(
                request,
                f'{service.name} has been added successfully.'
            )

            return redirect('accounts_admin:manage_services')
    else:
        form = ServiceForm(
            initial={'availability': 'active'}
        )

    context = {
        'form': form,
        'categories': form.fields['category'].queryset,
    }

    return render(
        request,
        'services/add_service.html',
        context,
    )

@role_required('admin')
def edit_service(request, service_id):
    """Update an existing service."""

    service = get_object_or_404(
        Service.objects.select_related('category'),
        pk=service_id,
    )

    if request.method == 'POST':
        form = ServiceForm(
            request.POST,
            request.FILES,
            instance=service,
        )

        if form.is_valid():
            service = form.save()

            messages.success(
                request,
                f'{service.name} has been updated successfully.'
            )

            return redirect(
                'accounts_admin:view_service',
                service_id=service.pk,
            )

    else:
        form = ServiceForm(
            instance=service,
            initial={
                'availability': (
                    'active' if service.is_active else 'inactive'
                )
            },
        )

    context = {
        'service': service,
        'form': form,
        'categories': form.fields['category'].queryset,
    }

    return render(
        request,
        'services/edit_service.html',
        context,
    )

@role_required('admin')
@require_POST
def deactivate_service(request, service_id):
    service = get_object_or_404(Service, pk=service_id)

    if service.is_active:
        service.is_active = False
        service.save(update_fields=['is_active'])

        messages.success(
            request,
            f'{service.name} has been deactivated successfully.'
        )
    else:
        messages.info(
            request,
            f'{service.name} is already inactive.'
        )

    return redirect(
        'accounts_admin:view_service',
        service_id=service.pk
    )

@role_required('admin')
def handyman_requests(request):
    service_requests = (
        HandymanProfileRequest.objects
        .filter(
            request_type=HandymanProfileRequest.TYPE_SERVICE
        )
        .select_related('handyman', 'reviewed_by')
        .order_by('-submitted_at', '-pk')
    )

    context = {
        'service_requests': service_requests,
        'request_count': service_requests.count(),
        'pending_count': service_requests.filter(
            status=HandymanProfileRequest.STATUS_PENDING
        ).count(),
    }

    return render(
        request,
        'services/handyman_requests.html',
        context
    )

def _resolve_requested_service(value, queryset):
    matches = list(
        queryset.filter(name__iexact=value.strip())[:2]
    )

    if not matches:
        raise ValidationError(
            f'Service "{value}" could not be found.'
        )

    if len(matches) > 1:
        raise ValidationError(
            f'Service "{value}" is ambiguous.'
        )

    return matches[0]


def _apply_service_request(service_request):
    profile = HandymanProfile.objects.select_for_update().filter(
        user=service_request.handyman
    ).first()

    if profile is None:
        raise ValidationError(
            'This handyman does not have a registered profile.'
        )

    action = service_request.action

    if action in (
        HandymanProfileRequest.ACTION_MODIFY,
        HandymanProfileRequest.ACTION_REMOVE
    ):
        current_service = _resolve_requested_service(
            service_request.current_value,
            profile.services.all()
        )

    if action in (
        HandymanProfileRequest.ACTION_ADD,
        HandymanProfileRequest.ACTION_MODIFY
    ):
        requested_service = _resolve_requested_service(
            service_request.requested_value,
            Service.objects.active()
        )

        if profile.services.filter(
            pk=requested_service.pk
        ).exists():
            raise ValidationError(
                'This service is already assigned to the handyman.'
            )

    if action == HandymanProfileRequest.ACTION_ADD:
        profile.services.add(requested_service)

    elif action == HandymanProfileRequest.ACTION_MODIFY:
        profile.services.remove(current_service)
        profile.services.add(requested_service)

    elif action == HandymanProfileRequest.ACTION_REMOVE:
        profile.services.remove(current_service)

    else:
        raise ValidationError('Invalid request action.')


@role_required('admin')
def review_service_request(request, request_id):

    service_request = get_object_or_404(
        HandymanProfileRequest.objects.select_related(
            'handyman', 'reviewed_by'
        ),
        pk=request_id,
        request_type=HandymanProfileRequest.TYPE_SERVICE
    )

    if request.method == 'POST':
        decision = request.POST.get('decision', '')
        note = request.POST.get('admin_note', '').strip()

        try:
            with transaction.atomic():

                service_request = get_object_or_404(
                    HandymanProfileRequest.objects.select_for_update(),
                    pk=request_id,
                    request_type=HandymanProfileRequest.TYPE_SERVICE
                )

                if service_request.status != HandymanProfileRequest.STATUS_PENDING:
                    raise ValidationError(
                        'This request has already been reviewed.'
                    )

                if decision not in ('approve', 'reject'):
                    raise ValidationError('Invalid decision.')

                if len(note) > 1000:
                    raise ValidationError(
                        'The decision note must not exceed 1000 characters.'
                    )

                if decision == 'reject' and not note:
                    raise ValidationError(
                        'Please provide a reason for rejection.'
                    )

                if decision == 'approve':
                    _apply_service_request(service_request)

                    service_request.status = (
                        HandymanProfileRequest.STATUS_APPROVED
                    )

                else:
                    service_request.status = (
                        HandymanProfileRequest.STATUS_REJECTED
                    )

                service_request.admin_note = note
                service_request.reviewed_by = request.user
                service_request.reviewed_at = timezone.now()

                service_request.save(update_fields=[
                    'status',
                    'admin_note',
                    'reviewed_by',
                    'reviewed_at',
                ])

            messages.success(
                request,
                f'Request {service_request.status} successfully.'
            )

        except ValidationError as error:
            messages.error(
                request,
                ' '.join(error.messages)
            )

        return redirect(
            'accounts_admin:review_service_request',
            request_id=request_id
        )

    context = {
        'service_request': service_request,
        'handyman_name': _person_name(service_request.handyman),
        'handyman_initials': _initials(service_request.handyman),
        'handyman_status': _account_status(service_request.handyman),
    }

    return render(
        request,
        'services/review_request.html',
        context
    )