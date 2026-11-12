from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse

from .permissions import role_required
from .services import get_admin_dashboard_stats


User = get_user_model()


class DashboardTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.customer = User.objects.create_user(
            username='test_customer',
            password='TestPass123!',
            role='customer'
        )

        self.handyman = User.objects.create_user(
            username='test_handyman',
            password='TestPass123!',
            role='handyman'
        )

        self.admin_user = User.objects.create_user(
            username='test_admin',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

    def test_customer_access(self):
        @role_required('customer')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.customer

        self.assertEqual(test_view(request).status_code, 200)

    def test_handyman_access(self):
        @role_required('handyman')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.handyman

        self.assertEqual(test_view(request).status_code, 200)

    def test_admin_access(self):
        @role_required('admin')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.admin_user

        self.assertEqual(test_view(request).status_code, 200)

    def test_customer_cannot_access_admin(self):
        @role_required('admin')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.customer

        self.assertEqual(test_view(request).status_code, 403)

    def test_dashboard_counts(self):
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_customers'], 1)
        self.assertEqual(stats['total_handymen'], 1)
        self.assertEqual(stats['total_admins'], 1)

    def test_inactive_users_not_counted(self):
        User.objects.create_user(
            username='inactive_customer',
            password='TestPass123!',
            role='customer',
            is_active=False
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_customers'], 1)

    def test_non_staff_admin_role_denied(self):
        user = User.objects.create_user(
            username='fake_admin',
            password='TestPass123!',
            role='admin',
            is_staff=False
        )

        @role_required('admin')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = user

        response = test_view(request)

        self.assertEqual(response.status_code, 403)
