
from django.contrib.auth import get_user_model
from .models import Notification
from django.db.models import Q


def notify_admins(notification_type, title, message):
    """
    Create a notification for every active administrator.
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
            message=message
        )
        for admin in admins
    ]

    return Notification.objects.bulk_create(notifications)
