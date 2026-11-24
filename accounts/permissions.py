from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def get_role(user):
    """Return 'admin', 'handyman', 'customer' or None."""
    if user.is_staff and (user.is_superuser or user.role == 'admin'):
        return 'admin'
    if user.role == 'admin':
        return None          # role says admin but not staff: refused
    return user.role


def role_required(*roles):
    """Allow only logged-in users whose role is in `roles`; others get a 403."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator


def approved_handyman_required(view):
    """Handyman whose profile has been approved by an administrator."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, 'handyman_profile', None)
        if request.user.role != 'handyman' or profile is None or not profile.is_approved:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return login_required(wrapper)