import re
import time

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from services.models import ServiceArea

from . import auth_messages as M
from . import validators, verification
from .models import HandymanProfile
from .permissions import get_role

User = get_user_model()

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

# ===================================================================== registration
FLOW_SECONDS = 30 * 60   # a registration session expires after 30 minutes
FLOW_KEYS = ('reg_role', 'reg_email', 'reg_verified', 'reg_pwhash', 'reg_provider', 'reg_ts')
EMAIL_RE = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
EMAIL_FAILED = 'We could not send the email. Please try again.'
REGISTER_COPY = {
    'wrong': M.REG_CODE_WRONG, 'expired': M.REG_CODE_EXPIRED, 'locked': M.REG_CODE_LOCKED,
    'hourly': M.REG_CODE_HOURLY, 'sent': M.REG_CODE_SENT,
}
CUSTOMER_FIELDS = ('first_name', 'surname', 'additional_names', 'username', 'phone', 'region', 'address')


def _touch(request):
    request.session['reg_ts'] = time.time()


def _stale(request):
    ts = request.session.get('reg_ts')
    return ts is None or time.time() - ts > FLOW_SECONDS


def _reset_flow(request):
    for key in FLOW_KEYS:
        request.session.pop(key, None)


def _role(request):
    role = request.session.get('reg_role') or request.GET.get('role') or 'customer'
    return role, (M.ROLE_PROVIDER if role == 'provider' else M.ROLE_CUSTOMER)


def _flow(request, step, **extra):
    """Context every registration page needs: step number, chosen role and the email."""
    role, label = _role(request)
    return {'step': step, 'role': role, 'role_label': label,
            'email': request.session.get('reg_email', ''), **extra}


def _regions():
    return [(a.name, a.name) for a in ServiceArea.objects.filter(is_active=True)]


# S02: choose a role
def register_role(request):
    if request.session.get('reg_ts') and _stale(request):
        _reset_flow(request)
    ctx = {'step': 0}
    if request.method == 'POST':
        role = request.POST.get('role')
        if role not in ('customer', 'provider'):
            ctx['error'] = M.ROLE_REQUIRED
            return render(request, 'accounts/register_role.html', ctx)
        request.session['reg_role'] = role
        _touch(request)
        return redirect('accounts:register_email')
    if request.session.get('reg_role'):
        ctx['role'] = request.session['reg_role']
    return render(request, 'accounts/register_role.html', ctx)


# S03: email address
def register_email(request):
    if request.session.get('reg_ts') and _stale(request):
        _reset_flow(request)
    ctx = _flow(request, 1, errors={})
    if request.method == 'POST':
        email = verification.normalise(request.POST.get('email'))
        ctx['email'] = email
        if not email:
            ctx['errors'] = {'email': M.EMAIL_REQUIRED}
        elif not EMAIL_RE.fullmatch(email):
            ctx['errors'] = {'email': M.REG_EMAIL_INVALID}
        elif User.objects.filter(email__iexact=email).exists():
            ctx['errors'] = {'email': M.REG_EMAIL_TAKEN}
            ctx['already_registered'] = True
        else:
            if email != request.session.get('reg_email'):   # a new email must be verified again
                request.session.pop('reg_verified', None)
                request.session.pop('reg_pwhash', None)
            request.session['reg_email'] = email
            _touch(request)
            return redirect('accounts:register_confirm')
    return render(request, 'accounts/register_email.html', ctx)


# S04: confirm the email, then send the code
def register_confirm(request):
    email = request.session.get('reg_email')
    if not email or _stale(request):
        return redirect('accounts:register_expired')
    ctx = _flow(request, 1, hint=M.REG_CONFIRM_HINT)
    if request.method == 'POST':
        try:
            code = verification.issue(email, 'register')
        except verification.VerificationLimit:
            return redirect('accounts:register_verify')   # the verify page shows the wait or limit
        if verification.send_code(email, code):
            _touch(request)
            return redirect('accounts:register_verify')
        ctx['hint'] = EMAIL_FAILED
    return render(request, 'accounts/register_confirm.html', ctx)


# S05: enter the 6-digit code
def register_verify(request):
    email = request.session.get('reg_email')
    if not email or _stale(request):
        return redirect('accounts:register_expired')
    state = alert = notice = ''
    if request.method == 'POST':
        if request.POST.get('action') == 'resend':
            try:
                code = verification.issue(email, 'register')
                if verification.send_code(email, code):
                    notice = REGISTER_COPY['sent']
                else:
                    alert = EMAIL_FAILED
            except verification.VerificationLimit as limit:
                if limit.reason == 'hourly':
                    state, alert = 'hourly', REGISTER_COPY['hourly']
                # 'cooldown': the page already shows the countdown
        else:
            code = request.POST.get('code', '').strip()
            result = verification.verify(email, 'register', code)
            if result == 'ok':
                request.session['reg_verified'] = True
                _touch(request)
                return redirect('accounts:register_password')
            state = {'wrong': 'wrong', 'expired': 'expired', 'none': 'expired', 'locked': 'locked'}[result]
            alert = REGISTER_COPY[state]
    numbers = verification.status(email, 'register')
    if not state and not alert and not notice and numbers['hourly'] and numbers['expires_in'] == 0:
        state, alert = 'hourly', REGISTER_COPY['hourly']
    ctx = _flow(request, 2, state=state, alert=alert, notice=notice,
                attempts_left=numbers['attempts_left'], expires_in=numbers['expires_in'],
                cooldown=numbers['cooldown'])
    return render(request, 'accounts/register_verify.html', ctx)


# S06: choose a password
def register_password(request):
    if not request.session.get('reg_verified') or _stale(request):
        return redirect('accounts:register_expired')
    ctx = _flow(request, 3, errors={}, rules=[(k, label, False) for k, label in M.PW_RULES])
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm', '')
        rules = validators.password_rules(password)
        ctx['rules'] = rules
        if not all(met for _, _, met in rules):
            ctx['errors'] = {'password': M.REG_PW_UNMET}
        elif password != confirm:
            ctx['errors'] = {'confirm': M.REG_PW_MISMATCH}
        else:
            request.session['reg_pwhash'] = make_password(password)   # only the hash is kept
            _touch(request)
            if _role(request)[0] == 'customer':
                return redirect('accounts:register_customer')
            return redirect('accounts:register_provider')
    return render(request, 'accounts/register_password.html', ctx)


# S07: the session timed out or a step was skipped
def register_expired(request):
    _reset_flow(request)
    return render(request, 'accounts/register_expired.html',
                  {'step': 0, 'message': M.REG_SESSION_EXPIRED})


# S08: customer details, this creates the account
def register_customer(request):
    if (request.session.get('reg_role') != 'customer' or not request.session.get('reg_verified')
            or not request.session.get('reg_pwhash') or _stale(request)):
        return redirect('accounts:register_expired')
    ctx = _flow(request, 4, errors={}, values={}, regions=_regions())
    if request.method == 'POST':
        values = {k: request.POST.get(k, '').strip() for k in CUSTOMER_FIELDS}
        terms, privacy = request.POST.get('terms'), request.POST.get('privacy')
        errors = validators.validate_customer(values, terms, privacy)
        ctx.update(values=values, errors=errors,
                   terms_accepted=bool(terms), privacy_accepted=bool(privacy))
        if not errors:
            now = timezone.now()
            try:
                with transaction.atomic():
                    User.objects.create(
                        username=values['username'], email=request.session['reg_email'],
                        first_name=values['first_name'], last_name=values['surname'],
                        additional_names=values['additional_names'], phone=values['phone'],
                        address=values['address'],
                        region=ServiceArea.objects.get(name=values['region']),
                        role='customer', password=request.session['reg_pwhash'],
                        terms_accepted_at=now, privacy_accepted_at=now)
            except IntegrityError:
                if validators.username_taken(values['username']):
                    ctx['errors'] = {'username': M.USERNAME_TAKEN}
                else:   # the email was registered by someone else in the meantime
                    return redirect('accounts:register_email')
            else:
                request.session['reg_name'] = f"{values['first_name']} {values['surname']}"
                for key in ('reg_role', 'reg_verified', 'reg_pwhash', 'reg_provider'):
                    request.session.pop(key, None)
                return redirect('accounts:register_done')
    return render(request, 'accounts/register_customer.html', ctx)


# S09: done (the user goes to the login page, there is no automatic login)
def register_done(request):
    name = request.session.get('reg_name')
    if not name:
        return redirect('accounts:register')
    return render(request, 'accounts/register_done.html',
                  {'step': 5, 'name': name, 'email': request.session.get('reg_email', '')})


# live username check used by the page while the user types
def username_check(request):
    username = request.GET.get('username', '').strip()
    if not validators.username_valid(username):
        return JsonResponse({'code': 'USERNAME_INVALID', 'message': M.CUSTOMER_ERRORS['username'],
                             'field': 'username'}, status=400)
    if validators.username_taken(username):
        return JsonResponse({'code': 'USERNAME_TAKEN', 'message': M.USERNAME_TAKEN,
                             'field': 'username'}, status=409)
    return JsonResponse({'available': True})