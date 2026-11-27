"""Adds `unread_count` (sidebar + bell badge) to every template for signed-in customers."""


def unread(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated or getattr(user, 'role', None) != 'customer':
        return {}
    return {'unread_count': user.notifications.filter(is_read=False).count()}
