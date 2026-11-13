from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bookings.models import ServiceRequest   # adjust if the model name changes
from .models import Payment, Quotation

User = get_user_model()


class ViewBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin1', password='x', role='admin')
        self.customer = User.objects.create_user('cust1', password='x', role='customer')
        self.other = User.objects.create_user('cust2', password='x', role='customer')
        self.req = ServiceRequest.objects.create(customer=self.customer)
        self.q = Quotation.objects.create(request=self.req, work_description='Fix leak',
                                          total_amount=Decimal('12500.00'), created_by=self.admin)
        self.q.send()

    def login(self, user):
        self.client.force_login(user)

    def pay_data(self, amount='12500.00'):
        return {'amount': amount, 'date_received': date.today().isoformat(), 'method': 'cash', 'reference': ''}


class AccessTests(ViewBase):
    def test_login_required(self):
        self.assertEqual(self.client.get(reverse('payments:quotation_list')).status_code, 302)

    def test_customer_cannot_use_admin_pages(self):
        self.login(self.customer)
        self.assertEqual(self.client.get(reverse('payments:quotation_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('payments:payment_record', args=[self.q.pk])).status_code, 403)

    def test_admin_cannot_use_customer_pages(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse('payments:my_quotations')).status_code, 403)

    def test_other_customer_cannot_see_quotation(self):
        self.login(self.other)
        self.assertEqual(self.client.get(reverse('payments:quotation_detail', args=[self.q.pk])).status_code, 404)


class QuotationViewTests(ViewBase):
    def test_admin_creates_and_sends(self):
        req2 = ServiceRequest.objects.create(customer=self.customer)
        self.login(self.admin)
        r = self.client.post(reverse('payments:quotation_create', args=[req2.pk]),
                             {'work_description': 'Paint wall', 'total_amount': '5000.00', 'send': '1'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Quotation.objects.get(request=req2).status, 'sent')

    def test_customer_accepts_and_declines(self):
        self.login(self.customer)
        self.client.post(reverse('payments:quotation_detail', args=[self.q.pk]), {'accept': '1'})
        self.q.refresh_from_db()
        self.assertEqual(self.q.status, 'accepted')

    def test_customer_declines(self):
        self.login(self.customer)
        self.client.post(reverse('payments:quotation_detail', args=[self.q.pk]), {'decline': '1'})
        self.q.refresh_from_db()
        self.assertEqual(self.q.status, 'declined')


class PaymentViewTests(ViewBase):
    def setUp(self):
        super().setUp()
        self.q.accept(self.customer)
        self.url = reverse('payments:payment_record', args=[self.q.pk])

    def test_admin_records_full_payment(self):
        self.login(self.admin)
        self.assertEqual(self.client.post(self.url, self.pay_data()).status_code, 302)
        self.assertTrue(Payment.objects.get().quotation.is_paid)

    def test_wrong_amount_shows_error_and_saves_nothing(self):
        self.login(self.admin)
        r = self.client.post(self.url, self.pay_data('100.00'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'full quotation total')
        self.assertEqual(Payment.objects.count(), 0)

    def test_duplicate_is_refused(self):
        self.login(self.admin)
        self.client.post(self.url, self.pay_data())
        self.client.post(self.url, self.pay_data())
        self.assertEqual(Payment.objects.count(), 1)

    def test_customer_sees_history(self):
        self.login(self.admin)
        self.client.post(self.url, self.pay_data())
        self.login(self.customer)
        self.assertContains(self.client.get(reverse('payments:payment_history')), '12500')


class BookingsContractTests(ViewBase):
    """bookings.Appointment.clean() runs this exact query. Do not rename these names."""

    def test_paid_accepted_quotation_query(self):
        query = Quotation.objects.filter(request_id=self.req.pk, status=Quotation.ACCEPTED, payment__isnull=False)
        self.assertFalse(query.exists())
        self.q.accept(self.customer)
        Payment.objects.create(quotation=self.q, amount=Decimal('12500.00'), date_received=date.today(),
                               method='cash', recorded_by=self.admin)
        self.assertTrue(query.exists())
