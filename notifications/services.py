

from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Notification


def notify_admins(notification_type, title, message, url=''):
    """
    Create a notification for every active administrator.
    Optionally include a destination URL.
    """

    User = get_user_model()

    admins = User.objects.filter(
        Q(role='admin') | Q(is_superuser=True),
        is_staff=True,
        is_active=True
    )

    notifications = [
        Notification(
            recipient=admin,
            notification_type=notification_type,
            title=title,
            message=message,
            url=url
        )
        for admin in admins
    ]

    return Notification.objects.bulk_create(notifications)

def notify_user(recipient, notification_type, title, message, url=''):
    """
    Create a notification for a specific active user.
    Supports customers, handymen and administrators.
    """

    if recipient is None or not recipient.is_active:
        return None

    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        url=url
    )