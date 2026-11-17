
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from jobs.models import Job
User = get_user_model()


class ReportsTests(TestCase):

    def setUp(self):
        self.url = reverse('reports:job_summary')

        self.admin_user = User.objects.create_user(
            username='report_admin',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.customer = User.objects.create_user(
            username='report_customer',
            password='TestPass123!',
            role='customer'
        )

        self.handyman = User.objects.create_user(
            username='report_handyman',
            password='TestPass123!',
            role='handyman'
        )

    def test_admin_can_access_report(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Job Summary Report')

    def test_customer_cannot_access_report(self):
        self.client.force_login(self.customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_handyman_cannot_access_report(self):
        self.client.force_login(self.handyman)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_redirected(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)


    def test_invalid_status_returns_all_jobs(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            self.url,
            {'status': 'invalid_status'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_jobs'], 0)


    def create_job(self, status=Job.ASSIGNED):
        return Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Plumbing',
            description='Repair leaking pipe',
            address='Port Louis',
            status=status
        )

    def test_report_counts_jobs_by_status(self):
        self.create_job(Job.ASSIGNED)
        self.create_job(Job.IN_PROGRESS)
        self.create_job(Job.COMPLETED)
        self.create_job(Job.CANCELLED)

        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_jobs'], 4)
        self.assertEqual(response.context['assigned_jobs'], 1)
        self.assertEqual(response.context['in_progress_jobs'], 1)
        self.assertEqual(response.context['completed_jobs'], 1)
        self.assertEqual(response.context['cancelled_jobs'], 1)

    def test_filter_by_job_status(self):
        self.create_job(Job.ASSIGNED)
        self.create_job(Job.COMPLETED)

        self.client.force_login(self.admin_user)
        response = self.client.get(
            self.url,
            {'status': Job.COMPLETED}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_jobs'], 1)
        self.assertEqual(response.context['completed_jobs'], 1)
        self.assertEqual(response.context['assigned_jobs'], 0)

    def test_invalid_status_shows_error(self):
        self.create_job()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            self.url,
            {'status': 'invalid_status'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['filters_valid'])
        self.assertIn(
            'Invalid job status selected.',
            response.context['errors']
        )
        self.assertEqual(response.context['total_jobs'], 0)

    def test_filter_by_start_date(self):
        self.create_job()

        self.client.force_login(self.admin_user)
        response = self.client.get(
            self.url,
            {'start_date': '2020-01-01'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_jobs'], 1)

    def test_filter_by_end_date(self):
        self.create_job()

        self.client.force_login(self.admin_user)
        response = self.client.get(
            self.url,
            {'end_date': '2020-01-01'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_jobs'], 0)

    def test_invalid_start_date(self):
        self.create_job()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            self.url,
            {'start_date': 'invalid-date'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['filters_valid'])
        self.assertIn(
            'Invalid start date.',
            response.context['errors']
        )

    def test_invalid_end_date(self):
        self.create_job()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            self.url,
            {'end_date': 'invalid-date'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['filters_valid'])
        self.assertIn(
            'Invalid end date.',
            response.context['errors']
        )

    def test_start_date_after_end_date(self):
        self.create_job()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            self.url,
            {
                'start_date': '2026-12-31',
                'end_date': '2026-01-01'
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['filters_valid'])
        self.assertIn(
            'Start date cannot be later than end date.',
            response.context['errors']
        )
        self.assertEqual(response.context['total_jobs'], 0)

    def test_empty_report(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_jobs'], 0)
        self.assertContains(response, 'No jobs available.')
