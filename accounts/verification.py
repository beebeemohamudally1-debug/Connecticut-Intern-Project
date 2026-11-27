import secrets
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import EmailVerification

CODE_LIFETIME = 300     # seconds a code stays valid (5 minutes)
MAX_ATTEMPTS = 3        # wrong tries before the code is locked
COOLDOWN = 60           # seconds before another code can be requested
MAX_PER_HOUR = 5        # codes per email per hour


class VerificationLimit(Exception):
    """Raised when a new code cannot be issued. reason is 'hourly' or 'cooldown'."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def normalise(email):
    return (email or '').strip().lower()


def _hash(code):
    return salted_hmac('accounts.verification', code).hexdigest()


def _latest(email, purpose):
    return (EmailVerification.objects
            .filter(email=email, purpose=purpose)
            .order_by('-created_at').first())


def issue(email, purpose):
    """Create a new code and return it. Raises VerificationLimit if not allowed."""
    email = normalise(email)
    now = timezone.now()
    last_hour = EmailVerification.objects.filter(
        email=email, purpose=purpose, created_at__gte=now - timedelta(hours=1))
    if last_hour.count() >= MAX_PER_HOUR:
        raise VerificationLimit('hourly')
    latest = _latest(email, purpose)
    if latest and (now - latest.created_at).total_seconds() < COOLDOWN:
        raise VerificationLimit('cooldown')
    code = f'{secrets.randbelow(10**6):06d}'
    EmailVerification.objects.create(email=email, purpose=purpose, code_hash=_hash(code))
    return code


def verify(email, purpose, code):
    """Return 'ok', 'wrong', 'expired', 'locked' or 'none'. Only the newest code counts."""
    email = normalise(email)
    record = _latest(email, purpose)
    if record is None or record.used:
        return 'none'
    age = (timezone.now() - record.created_at).total_seconds()
    if age > CODE_LIFETIME:
        return 'expired'
    if record.attempts >= MAX_ATTEMPTS:
        return 'locked'
    if constant_time_compare(_hash((code or '').strip()), record.code_hash):
        record.used = True
        record.save(update_fields=['used'])
        return 'ok'
    record.attempts += 1
    record.save(update_fields=['attempts'])
    return 'locked' if record.attempts >= MAX_ATTEMPTS else 'wrong'


def status(email, purpose):
    """Numbers the verify page shows: attempts_left, expires_in, cooldown, hourly."""
    email = normalise(email)
    now = timezone.now()
    latest = _latest(email, purpose)
    if latest is None:
        return {'attempts_left': 0, 'expires_in': 0, 'cooldown': 0, 'hourly': False}
    age = (now - latest.created_at).total_seconds()
    hourly = EmailVerification.objects.filter(
        email=email, purpose=purpose, created_at__gte=now - timedelta(hours=1)
    ).count() >= MAX_PER_HOUR
    return {
        'attempts_left': max(MAX_ATTEMPTS - latest.attempts, 0),
        'expires_in': max(int(CODE_LIFETIME - age), 0),
        'cooldown': max(int(COOLDOWN - age), 0),
        'hourly': hourly,
    }


def send_code(email, code):
    """Email the code. Returns True if it was sent."""
    try:
        send_mail(
            'Your HandyConnect verification code',
            f'Your verification code is {code}. It expires in 5 minutes. '
            'If you did not request it, you can ignore this email.',
            None, [normalise(email)])
        return True
    except Exception:
        return False