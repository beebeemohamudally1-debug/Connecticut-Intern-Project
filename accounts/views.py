import re
import time
import uuid

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from services.models import ServiceArea, ServiceCategory

from . import auth_messages as M
from . import validators, verification
from .models import HandymanProfile, ProviderDocument
from .permissions import get_role, role_required

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

# ===================================================================== provider registration
PROVIDER_FIELDS = ('first_name', 'surname', 'additional_names', 'username', 'phone', 'address')
FILE_RULES = {'types': ','.join(M.DOC_TYPES), 'max_mb': M.DOC_MAX_MB,
              'type_error': M.FILE_TYPE_ERROR, 'size_error': M.FILE_SIZE_ERROR}


def _provider_flow(request, step, **extra):
    return {**_flow(request, step, **extra), 'role': 'provider', 'role_label': M.ROLE_PROVIDER}


def _categories():
    return [(c.name, c.name) for c in ServiceCategory.objects.filter(is_active=True)]


def _provider_ready(request):
    session = request.session
    return bool(session.get('reg_role') == 'provider' and session.get('reg_verified')
                and session.get('reg_pwhash') and not _stale(request))


def _discard(documents):
    # Delete files written before a failure, so no orphan IDs stay on disk.
    for document in documents:
        try:
            document.file.delete(save=False)
        except OSError:
            pass


# S10: provider details. Nothing is created here; the answers wait in the session.
def register_provider(request):
    if not _provider_ready(request):
        return redirect('accounts:register_expired')
    saved = request.session.get('reg_provider', {})
    ctx = _provider_flow(
        request, 4, part='Part 1 of 2', errors={},
        values={k: saved.get(k, '') for k in PROVIDER_FIELDS},
        regions=_regions(), categories=_categories(),
        selected_regions=saved.get('regions', []), selected_categories=saved.get('categories', []))
    if request.method == 'POST':
        values = {k: request.POST.get(k, '').strip() for k in PROVIDER_FIELDS}
        regions = request.POST.getlist('regions')
        categories = request.POST.getlist('categories')
        errors = validators.validate_provider(values, regions, categories)
        ctx.update(values=values, errors=errors, selected_regions=regions, selected_categories=categories)
        if not errors:
            request.session['reg_provider'] = {**values, 'regions': regions, 'categories': categories}
            _touch(request)
            return redirect('accounts:register_provider_documents')
    return render(request, 'accounts/register_provider.html', ctx)

# S10b: documents. The account is created here, in ONE transaction.
def register_provider_documents(request):
    details = request.session.get('reg_provider')
    if not _provider_ready(request) or not details:
        return redirect('accounts:register_expired')
    name = details['first_name'] + ' ' + details['surname']
    ctx = _provider_flow(request, 4, part='Part 2 of 2', errors={}, name=name, file_rules=FILE_RULES)
    if request.method == 'POST':
        id_file = request.FILES.get('id_photo')
        certificates = request.FILES.getlist('certificates')
        terms, privacy = request.POST.get('terms'), request.POST.get('privacy')
        errors = validators.validate_documents(id_file, certificates, terms, privacy)
        ctx.update(errors=errors, terms_accepted=bool(terms), privacy_accepted=bool(privacy))
        if not errors:
            now = timezone.now()
            stored = []
            try:
                with transaction.atomic():
                    user = User.objects.create(
                        username=details['username'], email=request.session['reg_email'],
                        first_name=details['first_name'], last_name=details['surname'],
                        additional_names=details['additional_names'], phone=details['phone'],
                        address=details['address'], role='handyman',
                        password=request.session['reg_pwhash'],
                        terms_accepted_at=now, privacy_accepted_at=now)
                    profile = HandymanProfile.objects.create(user=user)   # status: PENDING_APPROVAL
                    profile.service_areas.set(ServiceArea.objects.filter(name__in=details['regions']))
                    profile.categories.set(ServiceCategory.objects.filter(name__in=details['categories']))
                    uploads = [(ProviderDocument.KIND_ID, id_file)]
                    uploads += [(ProviderDocument.KIND_CERTIFICATE, c) for c in certificates]
                    for kind, f in uploads:
                        original = f.name
                        f.name = f'{uuid.uuid4().hex}{validators.check_image(f)[1]}'   # never trust the file name
                        document = ProviderDocument(profile=profile, kind=kind, file=f,
                                                    original_name=original[:255])
                        document.save()
                        stored.append(document)
            except IntegrityError:
                _discard(stored)
                if User.objects.filter(email__iexact=request.session['reg_email']).exists():
                    return redirect('accounts:register_email')
                details['username'] = ''        # the username was taken in the meantime
                request.session['reg_provider'] = details
                return redirect('accounts:register_provider')
            except OSError:
                _discard(stored)
                ctx['errors'] = {'id_photo': M.FILE_UPLOAD_FAILED}
            else:
                request.session['reg_name'] = name
                for key in ('reg_role', 'reg_verified', 'reg_pwhash', 'reg_provider'):
                    request.session.pop(key, None)
                return redirect('accounts:register_provider_done')
    return render(request, 'accounts/register_provider_documents.html', ctx)


# S11: submitted. No automatic login: the provider logs in later and sees the application status.
def register_provider_done(request):
    name = request.session.get('reg_name')
    if not name:
        return redirect('accounts:register')
    return render(request, 'accounts/register_provider_done.html', {
        'step': 5, 'role': 'provider', 'role_label': M.ROLE_PROVIDER,
        'name': name, 'email': request.session.get('reg_email', '')})
    
# ===================================================================== password reset
RESET_SECONDS = 30 * 60   # a reset session expires after 30 minutes
RESET_KEYS = ('reset_email', 'reset_verified', 'reset_ts')
RESET_COPY = {'wrong': M.CODE_WRONG, 'expired': M.CODE_EXPIRED,
              'locked': M.CODE_LOCKED, 'hourly': M.CODE_HOURLY}


def _reset_touch(request):
    request.session['reset_ts'] = time.time()


def _reset_stale(request):
    ts = request.session.get('reset_ts')
    return ts is None or time.time() - ts > RESET_SECONDS


def _reset_clear(request):
    for key in RESET_KEYS:
        request.session.pop(key, None)


def _eligible_user(email):
    """The account that may reset: it exists, is active and is not suspended."""
    return User.objects.filter(email__iexact=email, is_active=True, is_suspended=False).first()


def _issue_reset_code(email):
    """Always create a code, but email it only if an account exists, so the page
    behaves the same for every address. Returns '' or the limit reason."""
    try:
        code = verification.issue(email, 'reset')
    except verification.VerificationLimit as limit:
        return limit.reason
    if _eligible_user(email):
        verification.send_code(email, code)
    return ''


def _notify_password_changed(user):
    try:
        send_mail('Your HandyConnect password was changed',
                  'Your password was changed. If this was not you, contact an administrator.',
                  None, [user.email])
    except Exception:
        pass


# Step 1: ask for the email. The answer is the same whether or not the account exists.
def forgot_password(request):
    ctx = {'errors': {}, 'email': '', 'panel': 'story'}
    if request.method == 'POST':
        email = verification.normalise(request.POST.get('email'))
        ctx['email'] = email
        if not email:
            ctx['errors'] = {'email': M.EMAIL_REQUIRED}
        elif not EMAIL_RE.fullmatch(email):
            ctx['errors'] = {'email': M.REG_EMAIL_INVALID}
        else:
            _reset_clear(request)
            _issue_reset_code(email)
            request.session['reset_email'] = email
            _reset_touch(request)
            ctx.update(submitted=True, notice=M.FORGOT_GENERIC)
    return render(request, 'accounts/forgot.html', ctx)


# Step 2: enter the 6-digit code.
def reset_verify(request):
    email = request.session.get('reset_email')
    if not email or _reset_stale(request):
        return redirect('accounts:forgot_password')
    state = alert = notice = ''
    if request.method == 'POST':
        if request.POST.get('action') == 'resend':
            reason = _issue_reset_code(email)
            if reason == 'hourly':
                state, alert = 'hourly', RESET_COPY['hourly']
            elif not reason:
                notice = M.REG_CODE_SENT
            # cooldown: the page already shows the countdown
        else:
            result = verification.verify(email, 'reset', request.POST.get('code', '').strip())
            if result == 'ok':
                request.session['reset_verified'] = True
                _reset_touch(request)
                return redirect('accounts:reset_new')
            state = {'wrong': 'wrong', 'expired': 'expired', 'none': 'expired', 'locked': 'locked'}[result]
            alert = RESET_COPY[state]
    numbers = verification.status(email, 'reset')
    if not state and numbers['hourly'] and numbers['expires_in'] == 0:
        state, alert = 'hourly', RESET_COPY['hourly']
    return render(request, 'accounts/reset_verify.html', {
        'panel': 'story', 'email': email, 'state': state, 'alert': alert, 'notice': notice,
        'attempts_left': numbers['attempts_left'], 'expires_in': numbers['expires_in'],
        'cooldown': numbers['cooldown']})


# Step 3: choose the new password.
def reset_new(request):
    email = request.session.get('reset_email')
    if not request.session.get('reset_verified') or not email or _reset_stale(request):
        return redirect('accounts:forgot_password')
    ctx = {'errors': {}, 'panel': 'story', 'rules': [(k, label, False) for k, label in M.PW_RULES]}
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm', '')
        rules = validators.password_rules(password)
        ctx['rules'] = rules
        if not all(met for _, _, met in rules):
            ctx['errors'] = {'password': M.RESET_RULES_UNMET}
        elif password != confirm:
            ctx['errors'] = {'confirm': M.RESET_MISMATCH}
        else:
            user = _eligible_user(email)
            if user is None:                      # the account changed in the meantime
                _reset_clear(request)
                return redirect('accounts:forgot_password')
            user.set_password(password)           # other sessions stop working: Django ties them to the old hash
            user.must_change_password = False
            user.save(update_fields=['password', 'must_change_password'])
            cache.delete(_fail_key(email))        # clear the login lock for this email
            _notify_password_changed(user)
            _reset_clear(request)
            return redirect('accounts:reset_done')
    return render(request, 'accounts/reset_new.html', ctx)

# ===================================================================== provider status
@role_required('handyman')
def provider_status(request):
    """The logged-in handyman's own application status. Nobody else can see it."""
    user = request.user
    profile = getattr(user, 'handyman_profile', None)
    return render(request, 'accounts/provider_status.html', {
        'display_name': user.get_full_name() or user.username,
        'email': user.email,
        # a handyman created by an administrator has no application: treat as active
        'account_status': profile.status if profile else HandymanProfile.STATUS_ACTIVE,
        'rejection_reason': profile.rejection_reason if profile else '',
    })