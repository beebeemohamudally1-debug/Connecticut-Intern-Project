from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import HandymanProfile
from accounts.permissions import role_required

User = get_user_model()
PASSWORD = 'Str0ngPass!word'


class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            username='cust1', email='cust1@example.com', password=PASSWORD, role='customer')

    def test_customer_login_redirects_to_dashboard(self):
        r = self.client.post(reverse('accounts:login'), {'email': 'CUST1@example.com', 'password': PASSWORD})
        self.assertRedirects(r, reverse('dashboard:customer_dashboard'), fetch_redirect_response=False)

    def test_wrong_password_rejected(self):
        r = self.client.post(reverse('accounts:login'), {'email': 'cust1@example.com', 'password': 'nope'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Invalid email or password')

    def test_suspended_user_blocked_after_password_check(self):
        self.customer.is_suspended = True
        self.customer.save()
        r = self.client.post(reverse('accounts:login'), {'email': 'cust1@example.com', 'password': PASSWORD})
        self.assertContains(r, 'suspended')

    def test_locked_after_five_failures(self):
        for _ in range(5):
            self.client.post(reverse('accounts:login'), {'email': 'cust1@example.com', 'password': 'bad'})
        r = self.client.post(reverse('accounts:login'), {'email': 'cust1@example.com', 'password': PASSWORD})
        self.assertContains(r, 'locked')

    def test_pending_handyman_goes_to_status_page(self):
        h = User.objects.create_user(username='h1', email='h1@example.com', password=PASSWORD, role='handyman')
        HandymanProfile.objects.create(user=h)
        r = self.client.post(reverse('accounts:login'), {'email': 'h1@example.com', 'password': PASSWORD})
        self.assertRedirects(r, reverse('accounts:provider_status'), fetch_redirect_response=False)


class PermissionTests(TestCase):
    def test_customer_cannot_use_handyman_view(self):
        @role_required('handyman')
        def view(request):
            return HttpResponse('ok')

        request = RequestFactory().get('/x')
        request.user = User.objects.create_user(username='c2', email='c2@example.com', password=PASSWORD)
        with self.assertRaises(PermissionDenied):
            view(request)

# Create your tests here.
