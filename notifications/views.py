
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404
from .models import Notification


def is_admin_user(user):
    return (
        user.is_authenticated
        and user.is_staff
        and (user.is_superuser or user.role == 'admin')
    )
    


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            return JsonResponse(
                {'error': 'Access denied'},
                status=403
            )
        return view_func(request, *args, **kwargs)
    return wrapper


@require_GET
@admin_required
def notification_list(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    )

    data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
        }
        for n in notifications
    ]

    return JsonResponse({'notifications': data})


@require_GET
@admin_required
def unread_count(request):
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return JsonResponse({'unread_count': count})


@require_POST
@admin_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.is_read = True
    notification.save(update_fields=['is_read'])

    return JsonResponse({'success': True})


@require_POST
@admin_required
def mark_all_as_read(request):
    updated = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({
        'success': True,
        'updated': updated
    })

