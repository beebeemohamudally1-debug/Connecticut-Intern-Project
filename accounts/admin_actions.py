from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.permissions import role_required

User = get_user_model()


def _target(request, pk):
    """The customer or handyman an administrator acts on. Never an administrator, never yourself."""
    user = get_object_or_404(User, pk=pk, role__in=('customer', 'handyman'),
                             is_staff=False, is_superuser=False)
    if user.pk == request.user.pk:
        raise Http404
    return user


def _back(user):
    name = 'accounts_admin:handyman_profile' if user.role == 'handyman' else 'accounts_admin:customer_detail'
    return redirect(name, pk=user.pk)


def _end_sessions(user):
    """Log the person out everywhere, so a suspended or deleted user cannot keep using the site."""
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if session.get_decoded().get('_auth_user_id') == str(user.pk):
            session.delete()


@role_required('admin')
@require_POST
def suspend_user(request, pk):
    user = _target(request, pk)
    user.is_suspended = True
    user.save(update_fields=['is_suspended'])
    _end_sessions(user)
    return _back(user)


@role_required('admin')
@require_POST
def reactivate_user(request, pk):
    user = _target(request, pk)
    user.is_suspended = False
    user.is_active = True
    user.save(update_fields=['is_suspended', 'is_active'])
    return _back(user)


@role_required('admin')
@require_POST
def delete_user(request, pk):
    user = _target(request, pk)
    user.is_active = False          # soft delete: related jobs, complaints and payments stay intact
    user.save(update_fields=['is_active'])
    _end_sessions(user)
    return _back(user)