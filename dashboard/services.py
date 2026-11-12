from django.contrib.auth import get_user_model


def get_admin_dashboard_stats():
    User = get_user_model()

    return {
        'total_customers': User.objects.filter(
            role='customer',
            is_active=True
        ).count(),

        'total_handymen': User.objects.filter(
            role='handyman',
            is_active=True
        ).count(),

        'total_admins': User.objects.filter(
            role='admin',
            is_staff=True,
            is_active=True
        ).count(),
    }