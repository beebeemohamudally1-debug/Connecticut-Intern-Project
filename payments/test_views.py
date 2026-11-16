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


# ====================================================================== new features
import tempfile

from django.test import override_settings

from bookings.models import ServiceRequestAssignment
from .models import LabourEstimate, MaterialPurchaseRequest, MaterialReceipt
from .tests import png_file


class FeatureViewBase(ViewBase):
    def setUp(self):
        super().setUp()
        self.handyman = User.objects.create_user('hand1', password='x', role='handyman')
        ServiceRequestAssignment.objects.create(service_request=self.req, handyman=self.handyman, status='accepted')


class EstimateViewTests(FeatureViewBase):
    def test_handyman_without_accepted_assignment_is_refused(self):
        stranger = User.objects.create_user('hand2', password='x', role='handyman')
        self.login(stranger)
        self.assertEqual(self.client.get(reverse('payments:estimate_submit', args=[self.req.pk])).status_code, 403)

    def test_estimate_to_quotation_flow(self):
        self.login(self.handyman)
        self.client.post(reverse('payments:estimate_submit', args=[self.req.pk]), {'amount': '8000.00', 'breakdown': 'Two days'})
        estimate = LabourEstimate.objects.get()
        self.login(self.admin)
        self.assertContains(self.client.get(reverse('payments:estimate_list')), 'Two days')
        self.client.post(reverse('payments:estimate_action', args=[estimate.pk]), {'action': 'approve'})
        estimate.refresh_from_db()
        self.assertEqual(estimate.status, 'approved')
        req2 = ServiceRequest.objects.create(customer=self.customer)
        estimate.request = req2
        estimate.save()
        page = self.client.get(reverse('payments:quotation_create', args=[req2.pk]) + f'?estimate={estimate.pk}')
        self.assertContains(page, '8000.00')

    def test_reject_without_reason_is_refused(self):
        self.login(self.handyman)
        self.client.post(reverse('payments:estimate_submit', args=[self.req.pk]), {'amount': '8000.00', 'breakdown': ''})
        estimate = LabourEstimate.objects.get()
        self.login(self.admin)
        self.client.post(reverse('payments:estimate_action', args=[estimate.pk]), {'action': 'reject', 'note': ''})
        estimate.refresh_from_db()
        self.assertEqual(estimate.status, 'submitted')

    def test_revision_then_resubmit(self):
        estimate = LabourEstimate.objects.create(request=self.req, handyman=self.handyman, amount=Decimal('9000.00'))
        self.login(self.admin)
        self.client.post(reverse('payments:estimate_action', args=[estimate.pk]), {'action': 'revision', 'note': 'Lower'})
        self.login(self.handyman)
        self.client.post(reverse('payments:estimate_resubmit', args=[estimate.pk]), {'amount': '8000.00', 'breakdown': 'Less'})
        estimate.refresh_from_db()
        self.assertEqual((estimate.status, estimate.amount), ('submitted', Decimal('8000.00')))

    def test_customer_cannot_open_estimates(self):
        self.login(self.customer)
        self.assertEqual(self.client.get(reverse('payments:estimate_list')).status_code, 403)


class RevisionViewTests(FeatureViewBase):
    def test_customer_revision_admin_revise_and_reissue(self):
        self.login(self.customer)
        self.client.post(reverse('payments:quotation_detail', args=[self.q.pk]), {'revision': '1', 'note': 'Cheaper please'})
        self.q.refresh_from_db()
        self.assertEqual(self.q.status, 'revision_requested')
        self.login(self.admin)
        self.client.post(reverse('payments:quotation_edit', args=[self.q.pk]), {'work_description': 'Smaller job', 'total_amount': '10000.00'})
        self.q.refresh_from_db()
        self.assertEqual((self.q.status, self.q.total_amount), ('revised', Decimal('10000.00')))
        self.client.post(reverse('payments:quotation_send', args=[self.q.pk]))
        self.q.refresh_from_db()
        self.assertEqual((self.q.status, self.q.revision_number), ('sent', 2))

    def test_revision_without_note_changes_nothing(self):
        self.login(self.customer)
        self.client.post(reverse('payments:quotation_detail', args=[self.q.pk]), {'revision': '1', 'note': ''})
        self.q.refresh_from_db()
        self.assertEqual(self.q.status, 'sent')

    def test_admin_details_and_cancel(self):
        self.login(self.admin)
        self.assertContains(self.client.get(reverse('payments:quotation_detail_admin', args=[self.q.pk])), 'Payment readiness')
        self.client.post(reverse('payments:quotation_cancel', args=[self.q.pk]))
        self.q.refresh_from_db()
        self.assertEqual(self.q.status, 'cancelled')

    def test_payment_page_refuses_an_unaccepted_quotation(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse('payments:payment_record', args=[self.q.pk])).status_code, 302)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MaterialViewTests(FeatureViewBase):
    def test_full_material_flow(self):
        self.login(self.handyman)
        self.client.post(reverse('payments:material_request_submit', args=[self.req.pk]), {'items': 'Pipes', 'estimated_cost': '900.00'})
        purchase = MaterialPurchaseRequest.objects.get()
        self.login(self.admin)
        self.assertContains(self.client.get(reverse('payments:admin_materials')), 'Pipes')
        self.client.post(reverse('payments:material_request_action', args=[purchase.pk]), {'action': 'forward', 'total': '950.00'})
        purchase.refresh_from_db()
        self.assertEqual(purchase.quotation.total_amount, Decimal('950.00'))
        self.login(self.customer)
        self.client.post(reverse('payments:quotation_detail', args=[purchase.quotation.pk]), {'accept': '1'})
        self.login(self.handyman)
        self.client.post(reverse('payments:receipt_upload', args=[purchase.pk]), {'image': png_file(), 'amount_spent': '900.00'})
        receipt = MaterialReceipt.objects.get()
        self.login(self.admin)
        self.client.post(reverse('payments:receipt_action', args=[receipt.pk]), {'action': 'approve'})
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'approved')

    def test_receipt_before_acceptance_is_refused(self):
        purchase = MaterialPurchaseRequest.objects.create(request=self.req, handyman=self.handyman, items='Pipes', estimated_cost=Decimal('900.00'))
        purchase.forward(self.admin)
        self.login(self.handyman)
        self.client.post(reverse('payments:receipt_upload', args=[purchase.pk]), {'image': png_file(), 'amount_spent': '900.00'})
        self.assertEqual(MaterialReceipt.objects.count(), 0)

    def test_materials_pages_are_role_restricted(self):
        self.login(self.customer)
        self.assertEqual(self.client.get(reverse('payments:admin_materials')).status_code, 403)
        self.assertEqual(self.client.get(reverse('payments:my_materials')).status_code, 403)
