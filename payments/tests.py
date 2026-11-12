from django.test import TestCase
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from bookings.models import ServiceRequest   # adjust to the real model name
from .models import Payment, Quotation

User = get_user_model()


def make_request(customer, status='requested'):
    # Adjust the fields to match the real request model
    return ServiceRequest.objects.create(customer=customer, status=status)


class BaseCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin1', password='x', role='admin')
        self.customer = User.objects.create_user('cust1', password='x', role='customer')
        self.other = User.objects.create_user('cust2', password='x', role='customer')
        self.req = make_request(self.customer)
        self.q = Quotation.objects.create(
            request=self.req, work_description='Fix leak',
            total_amount=Decimal('12500.00'), created_by=self.admin)
        self.q.send()

    def pay(self, **over):
        data = dict(quotation=self.q, amount=Decimal('12500.00'), date_received=date.today(),
                    method='cash', recorded_by=self.admin)
        data.update(over)
        return Payment.objects.create(**data)


class QuotationWorkflowTests(BaseCase):
    def test_customer_can_accept(self):
        self.q.accept(self.customer)
        self.assertEqual(self.q.status, 'accepted')

    def test_customer_can_decline(self):
        self.q.decline(self.customer)
        self.assertEqual(self.q.status, 'declined')

    def test_other_customer_cannot_respond(self):
        with self.assertRaises(ValidationError):
            self.q.accept(self.other)

    def test_cannot_respond_twice(self):
        self.q.accept(self.customer)
        with self.assertRaises(ValidationError):
            self.q.decline(self.customer)


class PaymentRuleTests(BaseCase):
    def test_payment_on_accepted_quotation_works(self):
        self.q.accept(self.customer)
        self.pay()
        self.assertEqual(self.q.payment_state, 'paid')

    def test_unpaid_state(self):
        self.q.accept(self.customer)
        self.assertEqual(self.q.payment_state, 'unpaid')

    def test_cannot_pay_unaccepted_quotation(self):
        with self.assertRaises(ValidationError):
            self.pay()

    def test_cannot_pay_declined_quotation(self):
        self.q.decline(self.customer)
        with self.assertRaises(ValidationError):
            self.pay()

    def test_amount_must_be_exact(self):
        self.q.accept(self.customer)
        with self.assertRaises(ValidationError):
            self.pay(amount=Decimal('12000.00'))

    def test_duplicate_payment_rejected(self):
        self.q.accept(self.customer)
        self.pay()
        with self.assertRaises(ValidationError):
            self.pay()

    def test_cancelled_request_rejected(self):
        self.q.accept(self.customer)
        self.req.status = 'cancelled'
        self.req.save()
        with self.assertRaises(ValidationError):
            self.pay()

    def test_only_admin_can_record(self):
        self.q.accept(self.customer)
        with self.assertRaises(ValidationError):
            self.pay(recorded_by=self.customer)
