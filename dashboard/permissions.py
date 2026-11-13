from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user

            if 'admin' in allowed_roles:
                allowed = (
                    user.is_staff
                    and (
                        user.is_superuser
                        or user.role == 'admin'
                    )
                )
            else:
                allowed = user.role in allowed_roles

            if not allowed:
                return JsonResponse(
                    {'error': 'Access denied'},
                    status=403
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
