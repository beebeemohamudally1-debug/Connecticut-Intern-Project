from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from accounts import verification
from accounts.models import EmailVerification
from unittest.mock import patch
from accounts import auth_messages as M

from accounts.models import HandymanProfile
from accounts.permissions import role_required

import io
import shutil
import tempfile

from django.contrib.sessions.models import Session
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from django.core import mail
from accounts.views import _fail_key

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
            
class VerificationTests(TestCase):
    EMAIL = 'new@example.com'

    def test_correct_code_works_once(self):
        code = verification.issue(self.EMAIL, 'register')
        self.assertEqual(verification.verify(self.EMAIL, 'register', code), 'ok')
        self.assertEqual(verification.verify(self.EMAIL, 'register', code), 'none')

    def test_three_wrong_attempts_lock_the_code(self):
        code = verification.issue(self.EMAIL, 'register')
        self.assertEqual(verification.verify(self.EMAIL, 'register', '000000'), 'wrong')
        self.assertEqual(verification.verify(self.EMAIL, 'register', '000001'), 'wrong')
        self.assertEqual(verification.verify(self.EMAIL, 'register', '000002'), 'locked')
        self.assertEqual(verification.verify(self.EMAIL, 'register', code), 'locked')

    def test_expired_code(self):
        code = verification.issue(self.EMAIL, 'register')
        EmailVerification.objects.update(created_at=timezone.now() - timedelta(minutes=6))
        self.assertEqual(verification.verify(self.EMAIL, 'register', code), 'expired')

    def test_cooldown_blocks_immediate_resend(self):
        verification.issue(self.EMAIL, 'register')
        with self.assertRaises(verification.VerificationLimit) as ctx:
            verification.issue(self.EMAIL, 'register')
        self.assertEqual(ctx.exception.reason, 'cooldown')

    def test_hourly_limit(self):
        for _ in range(5):
            verification.issue(self.EMAIL, 'register')
            EmailVerification.objects.update(created_at=timezone.now() - timedelta(minutes=5))
        with self.assertRaises(verification.VerificationLimit) as ctx:
            verification.issue(self.EMAIL, 'register')
        self.assertEqual(ctx.exception.reason, 'hourly')

    def test_new_code_replaces_old_one(self):
        old = verification.issue(self.EMAIL, 'register')
        EmailVerification.objects.update(created_at=timezone.now() - timedelta(minutes=2))
        new = verification.issue(self.EMAIL, 'register')
        self.assertEqual(verification.verify(self.EMAIL, 'register', old), 'wrong')
        self.assertEqual(verification.verify(self.EMAIL, 'register', new), 'ok')

class RegistrationFlowTests(TestCase):
    EMAIL = 'anna@example.com'
    PASSWORD = 'Str0ngPass!word'
    DETAILS = {
        'first_name': 'Anna', 'surname': 'Dupont', 'additional_names': '', 'username': 'anna_d',
        'phone': '51234567', 'region': 'Flacq', 'address': '12 Main Road',
        'terms': 'on', 'privacy': 'on',
    }

    def setUp(self):
        # fixed code and no real email
        for target, kwargs in (('accounts.verification.send_code', {'return_value': True}),
                               ('accounts.verification.secrets.randbelow', {'return_value': 123456})):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def verify_email(self, email=None):
        self.client.post(reverse('accounts:register'), {'role': 'customer'})
        self.client.post(reverse('accounts:register_email'), {'email': email or self.EMAIL})
        self.client.post(reverse('accounts:register_confirm'))
        return self.client.post(reverse('accounts:register_verify'), {'code': '123456'})

    def reach_details_page(self):
        self.verify_email()
        self.client.post(reverse('accounts:register_password'),
                         {'password': self.PASSWORD, 'confirm': self.PASSWORD})

    def test_full_customer_registration_creates_user(self):
        self.reach_details_page()
        r = self.client.post(reverse('accounts:register_customer'), self.DETAILS)
        self.assertRedirects(r, reverse('accounts:register_done'), fetch_redirect_response=False)
        user = User.objects.get(email=self.EMAIL)
        self.assertEqual(user.role, 'customer')
        self.assertEqual(user.region.name, 'Flacq')
        self.assertTrue(user.check_password(self.PASSWORD))

    def test_registered_email_is_refused(self):
        User.objects.create_user(username='old', email=self.EMAIL, password=self.PASSWORD)
        self.client.post(reverse('accounts:register'), {'role': 'customer'})
        r = self.client.post(reverse('accounts:register_email'), {'email': self.EMAIL.upper()})
        self.assertEqual(r.context['errors']['email'], M.REG_EMAIL_TAKEN)

    def test_wrong_code_is_refused(self):
        self.client.post(reverse('accounts:register'), {'role': 'customer'})
        self.client.post(reverse('accounts:register_email'), {'email': self.EMAIL})
        self.client.post(reverse('accounts:register_confirm'))
        r = self.client.post(reverse('accounts:register_verify'), {'code': '000000'})
        self.assertEqual(r.context['state'], 'wrong')
        self.assertEqual(r.context['attempts_left'], 2)

    def test_cannot_skip_email_verification(self):
        self.client.post(reverse('accounts:register'), {'role': 'customer'})
        self.client.post(reverse('accounts:register_email'), {'email': self.EMAIL})
        r = self.client.get(reverse('accounts:register_password'))
        self.assertRedirects(r, reverse('accounts:register_expired'), fetch_redirect_response=False)

    def test_weak_password_is_refused(self):
        self.verify_email()
        r = self.client.post(reverse('accounts:register_password'), {'password': 'abc', 'confirm': 'abc'})
        self.assertIn('password', r.context['errors'])

    def test_bad_phone_is_refused(self):
        self.reach_details_page()
        r = self.client.post(reverse('accounts:register_customer'), {**self.DETAILS, 'phone': '123'})
        self.assertIn('phone', r.context['errors'])
        self.assertFalse(User.objects.filter(email=self.EMAIL).exists())

    def test_username_check(self):
        User.objects.create_user(username='taken_name', email='t@example.com', password=self.PASSWORD)
        url = reverse('accounts:username_check')
        self.assertEqual(self.client.get(url, {'username': 'free_name'}).status_code, 200)
        self.assertEqual(self.client.get(url, {'username': 'TAKEN_NAME'}).status_code, 409)
        self.assertEqual(self.client.get(url, {'username': 'a!'}).status_code, 400)
        
TEMP_MEDIA = tempfile.mkdtemp()


def image_file(name='doc.png', image_format='PNG'):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), 'white').save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/' + image_format.lower())


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProviderRegistrationTests(TestCase):
    EMAIL = 'marc@example.com'
    PASSWORD = 'Str0ngPass!word'
    DETAILS = {
        'first_name': 'Marc', 'surname': 'Lafleur', 'additional_names': '', 'username': 'marc_l',
        'phone': '57123456', 'address': '5 Rue Royale',
        'regions': ['Flacq', 'Moka'], 'categories': ['Plumbing', 'Electrical'],
    }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        for target, kwargs in (('accounts.verification.send_code', {'return_value': True}),
                               ('accounts.verification.secrets.randbelow', {'return_value': 123456})):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def reach_details_page(self):
        self.client.post(reverse('accounts:register'), {'role': 'provider'})
        self.client.post(reverse('accounts:register_email'), {'email': self.EMAIL})
        self.client.post(reverse('accounts:register_confirm'))
        self.client.post(reverse('accounts:register_verify'), {'code': '123456'})
        self.client.post(reverse('accounts:register_password'),
                         {'password': self.PASSWORD, 'confirm': self.PASSWORD})

    def reach_documents_page(self):
        self.reach_details_page()
        return self.client.post(reverse('accounts:register_provider'), self.DETAILS)

    def submit(self, **overrides):
        data = {'id_photo': image_file('id.png'),
                'certificates': [image_file('c1.jpg', 'JPEG'), image_file('c2.png')],
                'terms': 'on', 'privacy': 'on'}
        data.update(overrides)
        return self.client.post(reverse('accounts:register_provider_documents'), data)

    def test_full_registration_creates_pending_account(self):
        self.reach_documents_page()
        r = self.submit()
        self.assertRedirects(r, reverse('accounts:register_provider_done'), fetch_redirect_response=False)
        user = User.objects.get(email=self.EMAIL)
        self.assertEqual(user.role, 'handyman')
        profile = user.handyman_profile
        self.assertEqual(profile.status, HandymanProfile.STATUS_PENDING)
        self.assertEqual(profile.documents.filter(kind='id_photo').count(), 1)
        self.assertEqual(profile.documents.filter(kind='certificate').count(), 2)
        self.assertEqual(set(profile.service_areas.values_list('name', flat=True)), {'Flacq', 'Moka'})
        self.assertEqual(set(profile.categories.values_list('name', flat=True)), {'Plumbing', 'Electrical'})
        self.assertNotIn('_auth_user_id', self.client.session)   # no automatic login

    def test_fake_image_is_refused(self):
        self.reach_documents_page()
        fake = SimpleUploadedFile('id.png', b'this is not an image', content_type='image/png')
        r = self.submit(id_photo=fake)
        self.assertIn('id_photo', r.context['errors'])
        self.assertFalse(User.objects.filter(email=self.EMAIL).exists())

    def test_certificate_is_required(self):
        self.reach_documents_page()
        r = self.submit(certificates=[])
        self.assertIn('certificates', r.context['errors'])
        self.assertFalse(User.objects.filter(email=self.EMAIL).exists())

    def test_consent_is_required(self):
        self.reach_documents_page()
        r = self.submit(terms='')
        self.assertIn('terms', r.context['errors'])
        self.assertFalse(User.objects.filter(email=self.EMAIL).exists())

    def test_region_is_required(self):
        self.reach_details_page()
        r = self.client.post(reverse('accounts:register_provider'), {**self.DETAILS, 'regions': []})
        self.assertIn('regions', r.context['errors'])

    def test_documents_page_needs_details_first(self):
        r = self.client.get(reverse('accounts:register_provider_documents'))
        self.assertRedirects(r, reverse('accounts:register_expired'), fetch_redirect_response=False)
class AdminStatusTests(TestCase):
    def setUp(self):
        from accounts.admin_views import _account_status
        self.status = _account_status

    def test_normal_user_is_active(self):
        user = User.objects.create_user(username='a1', email='a1@example.com', password=PASSWORD)
        self.assertEqual(self.status(user), 'Active')

    def test_suspended_user_shows_as_suspended(self):
        user = User.objects.create_user(
            username='s1', email='s1@example.com', password=PASSWORD, is_suspended=True)
        self.assertEqual(self.status(user), 'Suspended')

    def test_deactivated_user_shows_as_suspended(self):
        user = User.objects.create_user(
            username='d1', email='d1@example.com', password=PASSWORD, is_active=False)
        self.assertEqual(self.status(user), 'Suspended')
        
class PasswordResetTests(TestCase):
    EMAIL = 'reset@example.com'
    OLD = 'Str0ngPass!word'
    NEW = 'N3wStrongPass!word'

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='rst', email=self.EMAIL, password=self.OLD)
        self.send_code = patch('accounts.verification.send_code', return_value=True).start()
        patch('accounts.verification.secrets.randbelow', return_value=123456).start()
        self.addCleanup(patch.stopall)

    def request_code(self, email=None):
        return self.client.post(reverse('accounts:forgot_password'), {'email': email or self.EMAIL})

    def verify_code(self, code='123456'):
        return self.client.post(reverse('accounts:reset_verify'), {'code': code})

    def test_full_reset_changes_password(self):
        self.request_code()
        r = self.verify_code()
        self.assertRedirects(r, reverse('accounts:reset_new'), fetch_redirect_response=False)
        r = self.client.post(reverse('accounts:reset_new'), {'password': self.NEW, 'confirm': self.NEW})
        self.assertRedirects(r, reverse('accounts:reset_done'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW))
        self.assertFalse(self.user.check_password(self.OLD))
        self.assertEqual(len(mail.outbox), 1)   # the password changed email

    def test_unknown_email_gets_same_answer_and_no_email(self):
        r = self.request_code('nobody@example.com')
        self.assertTrue(r.context['submitted'])
        self.assertEqual(r.context['notice'], M.FORGOT_GENERIC)
        self.send_code.assert_not_called()

    def test_suspended_user_gets_no_code(self):
        self.user.is_suspended = True
        self.user.save()
        r = self.request_code()
        self.assertTrue(r.context['submitted'])
        self.send_code.assert_not_called()

    def test_wrong_code_is_refused(self):
        self.request_code()
        r = self.verify_code('000000')
        self.assertEqual(r.context['state'], 'wrong')
        self.assertEqual(r.context['attempts_left'], 2)

    def test_cannot_skip_code_check(self):
        self.request_code()
        r = self.client.get(reverse('accounts:reset_new'))
        self.assertRedirects(r, reverse('accounts:forgot_password'), fetch_redirect_response=False)

    def test_weak_password_is_refused(self):
        self.request_code()
        self.verify_code()
        r = self.client.post(reverse('accounts:reset_new'), {'password': 'abc', 'confirm': 'abc'})
        self.assertIn('password', r.context['errors'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.OLD))

    def test_reset_clears_the_login_lock(self):
        cache.set(_fail_key(self.EMAIL), 5, 900)
        self.request_code()
        self.verify_code()
        self.client.post(reverse('accounts:reset_new'), {'password': self.NEW, 'confirm': self.NEW})
        self.assertIsNone(cache.get(_fail_key(self.EMAIL)))
        
class ProviderStatusTests(TestCase):
    def make_handyman(self, username, status=HandymanProfile.STATUS_PENDING, reason=''):
        user = User.objects.create_user(
            username=username, email=username + '@example.com', password=PASSWORD, role='handyman')
        HandymanProfile.objects.create(user=user, status=status, rejection_reason=reason)
        return user

    def test_login_is_required(self):
        r = self.client.get(reverse('accounts:provider_status'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r.url)

    def test_pending_handyman_sees_pending(self):
        self.client.force_login(self.make_handyman('pend1'))
        r = self.client.get(reverse('accounts:provider_status'))
        self.assertEqual(r.context['account_status'], 'PENDING_APPROVAL')
        self.assertContains(r, 'under review')

    def test_rejected_handyman_sees_the_reason(self):
        self.client.force_login(self.make_handyman('rej1', HandymanProfile.STATUS_REJECTED, 'ID photo unreadable'))
        r = self.client.get(reverse('accounts:provider_status'))
        self.assertEqual(r.context['account_status'], 'REJECTED')
        self.assertContains(r, 'ID photo unreadable')

    def test_customer_is_refused(self):
        customer = User.objects.create_user(username='cus9', email='cus9@example.com', password=PASSWORD)
        self.client.force_login(customer)
        r = self.client.get(reverse('accounts:provider_status'))
        self.assertEqual(r.status_code, 403)

    def test_handyman_sees_only_their_own_status(self):
        mine = self.make_handyman('mine1')
        self.make_handyman('other1')
        self.client.force_login(mine)
        r = self.client.get(reverse('accounts:provider_status'))
        self.assertContains(r, 'mine1@example.com')
        self.assertNotContains(r, 'other1@example.com')
        
class AdminProfileTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='adm1', email='adm1@example.com', password=PASSWORD,
            role='admin', is_staff=True, first_name='Ada', last_name='Lovelace')
        self.other = User.objects.create_user(username='oth1', email='oth1@example.com', password=PASSWORD)
        self.url = reverse('accounts_admin:profile')
        self.client.force_login(self.admin)

    def test_saves_name_and_email(self):
        r = self.client.post(self.url, {'full_name': 'Grace Hopper', 'email': 'Grace@Example.com'})
        self.assertEqual(r.status_code, 302)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.first_name, self.admin.last_name), ('Grace', 'Hopper'))
        self.assertEqual(self.admin.email, 'grace@example.com')

    def test_email_used_by_someone_else_is_refused(self):
        r = self.client.post(self.url, {'full_name': 'Ada Lovelace', 'email': 'oth1@example.com'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('already used', r.context['error'])
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, 'adm1@example.com')

    def test_invalid_email_is_refused(self):
        r = self.client.post(self.url, {'full_name': 'Ada Lovelace', 'email': 'not-an-email'})
        self.assertIn('valid email', r.context['error'])

    def test_empty_name_is_refused(self):
        r = self.client.post(self.url, {'full_name': '   ', 'email': 'adm1@example.com'})
        self.assertIn('full name', r.context['error'])

    def test_non_admin_cannot_open_the_page(self):
        self.client.force_login(self.other)
        r = self.client.get(self.url)
        self.assertIn(r.status_code, (302, 403, 404))
        
class AdminUserActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='adm2', email='adm2@example.com', password=PASSWORD, role='admin', is_staff=True)
        self.customer = User.objects.create_user(
            username='cus2', email='cus2@example.com', password=PASSWORD, role='customer')
        self.handyman = User.objects.create_user(
            username='han2', email='han2@example.com', password=PASSWORD, role='handyman')
        self.client.force_login(self.admin)

    def act(self, name, user):
        return self.client.post(reverse('accounts_admin:' + name, args=[user.pk]))

    def sessions_of(self, user):
        return sum(1 for s in Session.objects.all() if s.get_decoded().get('_auth_user_id') == str(user.pk))

    def test_suspend_then_reactivate_a_customer(self):
        r = self.act('suspend_user', self.customer)
        self.assertRedirects(r, reverse('accounts_admin:customer_detail', args=[self.customer.pk]),
                             fetch_redirect_response=False)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_suspended)
        self.act('reactivate_user', self.customer)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_suspended)
        self.assertTrue(self.customer.is_active)

    def test_suspend_a_handyman_goes_back_to_the_handyman_page(self):
        r = self.act('suspend_user', self.handyman)
        self.assertRedirects(r, reverse('accounts_admin:handyman_profile', args=[self.handyman.pk]),
                             fetch_redirect_response=False)

    def test_delete_deactivates_the_account(self):
        self.act('delete_user', self.customer)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())   # soft delete: the row stays

    def test_suspending_ends_the_users_open_sessions(self):
        Client().force_login(self.customer)
        self.assertEqual(self.sessions_of(self.customer), 1)
        self.act('suspend_user', self.customer)
        self.assertEqual(self.sessions_of(self.customer), 0)

    def test_get_request_is_refused(self):
        r = self.client.get(reverse('accounts_admin:suspend_user', args=[self.customer.pk]))
        self.assertEqual(r.status_code, 405)

    def test_non_admin_cannot_suspend(self):
        self.client.force_login(self.handyman)
        self.act('suspend_user', self.customer)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_suspended)

    def test_admin_cannot_act_on_themselves(self):
        r = self.act('suspend_user', self.admin)
        self.assertEqual(r.status_code, 404)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_suspended)

    def test_detail_pages_post_to_the_real_actions(self):
        r = self.client.get(reverse('accounts_admin:customer_detail', args=[self.customer.pk]))
        self.assertContains(r, reverse('accounts_admin:suspend_user', args=[self.customer.pk]))
        r = self.client.get(reverse('accounts_admin:handyman_profile', args=[self.handyman.pk]))
        self.assertContains(r, reverse('accounts_admin:delete_user', args=[self.handyman.pk]))
        
# Create your tests here.
