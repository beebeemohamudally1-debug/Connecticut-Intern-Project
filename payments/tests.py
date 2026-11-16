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


# ====================================================================== new features
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
import tempfile

from bookings.models import ServiceRequestAssignment
from .models import LabourEstimate, MaterialPurchaseRequest, MaterialReceipt, request_fully_paid, request_payment_state


def png_file(name='receipt.png'):
    from io import BytesIO
    from PIL import Image
    buffer = BytesIO()
    Image.new('RGB', (4, 4), 'white').save(buffer, 'PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class FeatureBase(BaseCase):
    def setUp(self):
        super().setUp()
        self.handyman = User.objects.create_user('hand1', password='x', role='handyman')
        self.other_handyman = User.objects.create_user('hand2', password='x', role='handyman')
        ServiceRequestAssignment.objects.create(service_request=self.req, handyman=self.handyman, status='accepted')

    def estimate(self, amount='8000.00'):
        return LabourEstimate.objects.create(request=self.req, handyman=self.handyman,
                                             amount=Decimal(amount), breakdown='2 days of work')


class LabourEstimateTests(FeatureBase):
    def test_admin_approves(self):
        e = self.estimate()
        e.approve(self.admin)
        self.assertEqual(e.status, 'approved')

    def test_only_admin_can_review(self):
        with self.assertRaises(ValidationError):
            self.estimate().approve(self.customer)

    def test_reject_and_revision_need_a_reason(self):
        with self.assertRaises(ValidationError):
            self.estimate().reject(self.admin, '')
        with self.assertRaises(ValidationError):
            self.estimate().request_revision(self.admin, '  ')

    def test_revision_cycle(self):
        e = self.estimate()
        e.request_revision(self.admin, 'Too high')
        e.resubmit(self.handyman, Decimal('7000.00'), 'Lower')
        self.assertEqual((e.status, e.amount), ('submitted', Decimal('7000.00')))

    def test_only_own_handyman_can_resubmit(self):
        e = self.estimate()
        e.request_revision(self.admin, 'Too high')
        with self.assertRaises(ValidationError):
            e.resubmit(self.other_handyman, Decimal('1.00'), '')

    def test_cannot_review_twice(self):
        e = self.estimate()
        e.approve(self.admin)
        with self.assertRaises(ValidationError):
            e.reject(self.admin, 'Changed my mind')


class QuotationRevisionTests(FeatureBase):
    def test_revision_cycle(self):
        self.q.request_revision(self.customer, 'Please lower the price')
        self.assertEqual(self.q.status, 'revision_requested')
        self.q.revise(self.admin, Decimal('11000.00'), 'Fix leak, smaller scope')
        self.assertEqual(self.q.status, 'revised')
        self.q.send()
        self.assertEqual((self.q.status, self.q.revision_number, self.q.total_amount), ('sent', 2, Decimal('11000.00')))
        self.q.accept(self.customer)
        self.assertEqual(self.q.status, 'accepted')

    def test_revision_needs_a_note(self):
        with self.assertRaises(ValidationError):
            self.q.request_revision(self.customer, '')

    def test_only_the_customer_can_request_revision(self):
        with self.assertRaises(ValidationError):
            self.q.request_revision(self.other, 'x')

    def test_only_a_sent_quotation_can_be_revised_by_customer(self):
        self.q.accept(self.customer)
        with self.assertRaises(ValidationError):
            self.q.request_revision(self.customer, 'x')

    def test_only_admin_can_revise(self):
        self.q.request_revision(self.customer, 'x')
        with self.assertRaises(ValidationError):
            self.q.revise(self.customer, Decimal('1.00'), 'x')

    def test_cancel(self):
        self.q.cancel(self.admin)
        self.assertEqual(self.q.status, 'cancelled')

    def test_paid_quotation_cannot_be_cancelled(self):
        self.q.accept(self.customer)
        Payment.objects.create(quotation=self.q, amount=Decimal('12500.00'), date_received=date.today(),
                               method='cash', recorded_by=self.admin)
        self.q.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.q.cancel(self.admin)


class QuotationTypeTests(FeatureBase):
    def test_labour_and_material_can_both_exist(self):
        m = Quotation(request=self.req, quotation_type='material', work_description='Pipes',
                      total_amount=Decimal('900.00'), created_by=self.admin)
        m.full_clean()
        m.save()
        self.assertEqual(Quotation.objects.filter(request=self.req).count(), 2)

    def test_two_live_quotations_of_one_type_are_refused(self):
        again = Quotation(request=self.req, work_description='Again', total_amount=Decimal('1.00'), created_by=self.admin)
        with self.assertRaises(ValidationError):
            again.full_clean()


class MaterialTests(FeatureBase):
    def purchase(self):
        return MaterialPurchaseRequest.objects.create(request=self.req, handyman=self.handyman,
                                                      items='Pipes and tape', estimated_cost=Decimal('900.00'))

    def test_forward_creates_a_sent_material_quotation(self):
        p = self.purchase()
        q = p.forward(self.admin)
        p.refresh_from_db()
        self.assertEqual((q.quotation_type, q.status, q.total_amount), ('material', 'sent', Decimal('900.00')))
        self.assertEqual((p.status, p.quotation), ('forwarded', q))

    def test_forward_can_change_the_total(self):
        q = self.purchase().forward(self.admin, Decimal('1000.00'))
        self.assertEqual(q.total_amount, Decimal('1000.00'))

    def test_only_admin_can_forward(self):
        with self.assertRaises(ValidationError):
            self.purchase().forward(self.handyman)

    def test_reject_needs_a_reason(self):
        with self.assertRaises(ValidationError):
            self.purchase().reject(self.admin, '')

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_receipt_only_after_customer_accepts(self):
        p = self.purchase()
        q = p.forward(self.admin)
        receipt = MaterialReceipt(purchase_request=p, uploaded_by=self.handyman, image=png_file(), amount_spent=Decimal('850.00'))
        with self.assertRaises(ValidationError):
            receipt.full_clean()
        q.accept(self.customer)
        p.refresh_from_db()
        receipt.full_clean()

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_receipt_review(self):
        p = self.purchase()
        p.forward(self.admin).accept(self.customer)
        r = MaterialReceipt.objects.create(purchase_request=p, uploaded_by=self.handyman, image=png_file(), amount_spent=Decimal('850.00'))
        with self.assertRaises(ValidationError):
            r.approve(self.handyman)
        r.approve(self.admin)
        self.assertEqual(r.status, 'approved')


class ReadinessTests(FeatureBase):
    def test_not_ready_until_accepted(self):
        self.assertFalse(self.q.ready_for_payment)
        self.assertIn('not been accepted', self.q.readiness_issue)

    def test_ready_when_accepted_and_unpaid(self):
        self.q.accept(self.customer)
        self.assertTrue(self.q.ready_for_payment)

    def test_not_ready_when_request_cancelled(self):
        self.q.accept(self.customer)
        self.req.status = 'cancelled'
        self.req.save()
        self.q.refresh_from_db()
        self.assertFalse(self.q.ready_for_payment)

    def test_request_payment_state_across_both_types(self):
        self.assertEqual(request_payment_state(self.req), 'none')
        self.q.accept(self.customer)
        self.assertEqual(request_payment_state(self.req), 'unpaid')
        material = Quotation.objects.create(request=self.req, quotation_type='material', work_description='Pipes',
                                            total_amount=Decimal('900.00'), created_by=self.admin)
        material.send()
        material.accept(self.customer)
        Payment.objects.create(quotation=self.q, amount=Decimal('12500.00'), date_received=date.today(),
                               method='cash', recorded_by=self.admin)
        self.assertEqual(request_payment_state(self.req), 'partial')
        self.assertFalse(request_fully_paid(self.req))
        Payment.objects.create(quotation=material, amount=Decimal('900.00'), date_received=date.today(),
                               method='cash', recorded_by=self.admin)
        self.assertTrue(request_fully_paid(self.req))
