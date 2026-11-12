from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from jobs.models import Job
from complaints.models import Complaint

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


    def test_job_statistics(self):
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_jobs'], 0)
        self.assertEqual(stats['assigned_jobs'], 0)
        self.assertEqual(stats['in_progress_jobs'], 0)
        self.assertEqual(stats['completed_jobs'], 0)
        self.assertEqual(stats['cancelled_jobs'], 0)


    def test_complaint_statistics(self):
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_complaints'], 0)
        self.assertEqual(stats['pending_complaints'], 0)
        self.assertEqual(stats['in_progress_complaints'], 0)
        self.assertEqual(stats['resolved_complaints'], 0)

    
    def test_job_statistics_with_records(self):
        Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Plumbing',
            description='Fix leaking pipe',
            address='Test Address',
            status=Job.ASSIGNED
        )

        Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Electrical',
            description='Repair light',
            address='Test Address',
            status=Job.COMPLETED
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_jobs'], 2)
        self.assertEqual(stats['assigned_jobs'], 1)
        self.assertEqual(stats['completed_jobs'], 1)
        self.assertEqual(stats['in_progress_jobs'], 0)
        self.assertEqual(stats['cancelled_jobs'], 0)


    def test_complaint_statistics_with_records(self):
        job = Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Plumbing',
            description='Fix leaking pipe',
            address='Test Address',
            status=Job.COMPLETED
        )

        Complaint.objects.create(
            submitted_by=self.customer,
            against=self.handyman,
            job=job,
            subject='Poor workmanship',
            description='The pipe is still leaking.',
            status=Complaint.PENDING
        )

        Complaint.objects.create(
            submitted_by=self.customer,
            against=self.handyman,
            job=job,
            subject='Delayed service',
            description='The repair was delayed.',
            status=Complaint.IN_PROGRESS
        )

        Complaint.objects.create(
            submitted_by=self.customer,
            against=self.handyman,
            job=job,
            subject='Service issue',
            description='The issue has been addressed.',
            status=Complaint.RESOLVED,
            outcome='Complaint investigated and resolved.'
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_complaints'], 3)
        self.assertEqual(stats['pending_complaints'], 1)
        self.assertEqual(stats['in_progress_complaints'], 1)
        self.assertEqual(stats['resolved_complaints'], 1)
