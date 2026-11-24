from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import auth_messages as M
from .models import HandymanProfile
from .permissions import get_role

MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


def _fail_key(email):
    return f'login-fails:{email}'


def _landing(user):
    """Where each kind of user goes after logging in."""
    role = get_role(user)
    if role == 'admin':
        return 'dashboard:admin_dashboard'
    if role == 'handyman':
        profile = getattr(user, 'handyman_profile', None)
        if profile and profile.is_approved:
            return 'dashboard:handyman_dashboard'
        return 'accounts:provider_status'
    return 'dashboard:customer_dashboard'


def login_view(request):
    ctx = {'errors': {}, 'email': '', 'panel': 'login'}
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        ctx['email'] = email

        if not email or not password:
            if not email:
                ctx['errors']['email'] = M.EMAIL_REQUIRED
            if not password:
                ctx['errors']['password'] = M.PASSWORD_REQUIRED
        elif cache.get(_fail_key(email), 0) >= MAX_ATTEMPTS:
            ctx['alert'] = M.LOCKED
        else:
            user = authenticate(request, email=email, password=password)
            if user is None:
                fails = cache.get(_fail_key(email), 0) + 1
                cache.set(_fail_key(email), fails, LOCK_SECONDS)
                ctx['alert'] = M.INVALID_CREDENTIALS
            else:
                cache.delete(_fail_key(email))
                profile = getattr(user, 'handyman_profile', None)
                if user.is_suspended:
                    ctx['alert'] = M.SUSPENDED
                elif not user.is_active:
                    ctx['alert'] = M.DISABLED
                elif profile and profile.status == HandymanProfile.STATUS_REJECTED:
                    ctx['alert'] = M.REJECTED.format(reason=profile.rejection_reason)
                else:
                    login(request, user, backend='accounts.backends.EmailBackend')
                    return redirect(_landing(user))
    return render(request, 'accounts/login.html', ctx)


@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')
