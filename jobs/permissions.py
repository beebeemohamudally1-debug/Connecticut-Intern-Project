from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def get_role(user):
    """Return 'admin', 'handyman' or 'customer'.

    An admin needs role 'admin' AND staff enabled (same rule as the
    notifications app). An 'admin' without staff gets None and is refused.
    """
    if user.role == 'admin':
        return 'admin' if user.is_staff else None
    return user.role


def role_required(*roles):
    """Require a logged-in user whose role is one of `roles`."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator


def base_template_for(user):
    return 'base_admin.html' if get_role(user) == 'admin' else 'jobs/base_user.html'