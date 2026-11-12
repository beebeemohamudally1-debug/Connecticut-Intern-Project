
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

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
