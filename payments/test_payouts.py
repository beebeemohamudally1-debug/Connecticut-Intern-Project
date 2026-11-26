import tempfile
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bookings.models import ServiceRequest, ServiceRequestAssignment
from jobs.models import Job

from .models import Invoice, LabourEstimate, MaterialPurchaseRequest, MaterialReceipt, Quotation
from .payouts import (HandymanPayout, handyman_earnings, jobs_ready_for_payout, jobs_waiting_for_customer_payment,
                      suggested_amounts)

User = get_user_model()


def image(name='proof.png', content_type='image/png'):
    from PIL import Image
    buffer = BytesIO()
    Image.new('RGB', (4, 4), 'white').save(buffer, 'PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PayoutBase(TestCase):
    """A handyman, a customer and an administrator, plus helpers to build a funded job."""

    def setUp(self):
        self.admin = User.objects.create_user('admin1', password='x', role='admin')
        self.customer = User.objects.create_user('cust1', password='x', role='customer')
        self.handyman = User.objects.create_user('hand1', password='x', role='handyman')
        self.other_handyman = User.objects.create_user('hand2', password='x', role='handyman')

    def make_job(self, *, pay_invoice=True, estimate=True, receipt=True, completed=True, labour_total='12000.00', material_total='900.00'):
        sr = ServiceRequest.objects.create(customer=self.customer, status='booked')
        ServiceRequestAssignment.objects.create(service_request=sr, handyman=self.handyman, status='accepted')
        est = None
        if estimate:
            est = LabourEstimate.objects.create(request=sr, handyman=self.handyman, amount=Decimal('8000.00'),
                                                breakdown='2 days', status='approved')
        labour = Quotation.objects.create(request=sr, labour_estimate=est, work_description='Fix leak',
                                          total_amount=Decimal(labour_total), created_by=self.admin)
        labour.send()
        labour.accept(self.customer)
        purchase = MaterialPurchaseRequest.objects.create(request=sr, handyman=self.handyman, items='Pipes',
                                                          estimated_cost=Decimal(material_total))
        purchase.forward(self.admin).accept(self.customer)
        if receipt:
            r = MaterialReceipt.objects.create(purchase_request=purchase, uploaded_by=self.handyman, image=image(),
                                               amount_spent=Decimal('850.00'))
            r.approve(self.admin)
        invoice = Invoice.issue_job(self.admin, sr, timezone.localdate() + timedelta(days=5))
        if pay_invoice:
            invoice.record_payment(self.admin, amount=invoice.total_amount, date_received=timezone.localdate(), method='cash', clear=True)
        job = Job.objects.create(service_request=sr, customer=self.customer, handyman=self.handyman, service_name='Plumbing',
                                 description='Leak', address='1 Main St', status='completed' if completed else 'in_progress')
        return job

    def pay(self, job, **over):
        data = dict(labour_amount=Decimal('8000.00'), materials_amount=Decimal('850.00'),
                    date_paid=timezone.localdate(), method='bank_transfer', reference='PAY-1')
        data.update(over)
        return HandymanPayout.record(self.admin, job, **data)


class RecordPayoutTests(PayoutBase):
    def test_records_a_payout(self):
        job = self.make_job()
        p = self.pay(job)
        self.assertEqual((p.status, p.handyman, p.amount), ('paid', self.handyman, Decimal('8850.00')))
        self.assertRegex(p.number, r'^PAY-\d{4}-0001$')

    def test_numbers_do_not_repeat(self):
        a, b = self.pay(self.make_job()), self.pay(self.make_job())
        self.assertNotEqual(a.number, b.number)

    def test_only_an_admin_can_record(self):
        job = self.make_job()
        with self.assertRaises(ValidationError):
            HandymanPayout.record(self.handyman, job, labour_amount=Decimal('1'), materials_amount=Decimal('0'),
                                  date_paid=date.today(), method='cash')

    def test_job_must_be_completed(self):
        with self.assertRaises(ValidationError):
            self.pay(self.make_job(completed=False))

    def test_customer_payment_must_be_cleared(self):
        with self.assertRaises(ValidationError):
            self.pay(self.make_job(pay_invoice=False))

    def test_job_without_a_request_is_refused(self):
        job = self.make_job()
        Job.objects.filter(pk=job.pk).update(service_request=None)
        job.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.pay(job)

    def test_no_second_payout_for_a_job(self):
        job = self.make_job()
        self.pay(job)
        with self.assertRaises(ValidationError):
            self.pay(job)

    def test_cannot_pay_more_than_the_customer_paid(self):
        job = self.make_job()                       # customer paid 12000 + 900 = 12900
        with self.assertRaises(ValidationError):
            self.pay(job, labour_amount=Decimal('12900.01'), materials_amount=Decimal('0'))
        self.pay(job, labour_amount=Decimal('12000.00'), materials_amount=Decimal('900.00'))

    def test_amount_rules(self):
        job = self.make_job()
        for bad in (dict(labour_amount=Decimal('0'), materials_amount=Decimal('0')),
                    dict(labour_amount=Decimal('-1')), dict(date_paid=date.today() + timedelta(days=1)),
                    dict(method='cheque')):
            with self.assertRaises(ValidationError):
                self.pay(job, **bad)
        self.assertEqual(HandymanPayout.objects.count(), 0)


class SuggestionAndCrossCheckTests(PayoutBase):
    def test_suggestion_uses_the_approved_estimate_and_receipts(self):
        self.assertEqual(suggested_amounts(self.make_job()), (Decimal('8000.00'), Decimal('850.00')))

    def test_no_estimate_means_labour_is_unknown(self):
        labour, materials = suggested_amounts(self.make_job(estimate=False))
        self.assertIsNone(labour)

    def test_unapproved_receipts_are_ignored(self):
        self.assertEqual(suggested_amounts(self.make_job(receipt=False))[1], Decimal('0.00'))

    def test_matching_payout_has_no_notes(self):
        p = self.pay(self.make_job())
        self.assertEqual(p.cross_check, [])
        self.assertEqual(p.platform_margin, Decimal('4050.00'))     # 12900 - 8850

    def test_difference_from_the_estimate_is_flagged(self):
        p = self.pay(self.make_job(), labour_amount=Decimal('9000.00'))
        self.assertEqual(len(p.cross_check), 1)
        self.assertIn('estimate', p.cross_check[0])


class ConfirmPayoutTests(PayoutBase):
    def setUp(self):
        super().setUp()
        self.job = self.make_job()
        self.payout = self.pay(self.job)

    def test_handyman_confirms(self):
        self.payout.confirm(self.handyman)
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, 'confirmed')
        self.assertIsNotNone(self.payout.confirmed_at)

    def test_confirming_moves_the_job_to_finished_work(self):
        self.payout.confirm(self.handyman)
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_stage, Job.PAYOUT_FINISHED)

    def test_another_handyman_or_the_admin_cannot_confirm(self):
        for user in (self.other_handyman, self.admin):
            with self.assertRaises(ValidationError):
                self.payout.confirm(user)

    def test_cannot_confirm_twice(self):
        self.payout.confirm(self.handyman)
        with self.assertRaises(ValidationError):
            self.payout.confirm(self.handyman)

    def test_proof_is_saved(self):
        self.payout.confirm(self.handyman, image())
        self.payout.refresh_from_db()
        self.assertTrue(self.payout.proof_image.name.startswith('receipts/payouts/'))

    def test_a_wrong_file_type_is_refused_and_nothing_changes(self):
        with self.assertRaises(ValidationError):
            self.payout.confirm(self.handyman, SimpleUploadedFile('proof.txt', b'hello', content_type='text/plain'))
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, 'paid')


class ListAndEarningsTests(PayoutBase):
    def test_ready_and_waiting_lists(self):
        ready, waiting = self.make_job(), self.make_job(pay_invoice=False)
        self.assertEqual(list(jobs_ready_for_payout()), [ready])
        self.assertEqual(list(jobs_waiting_for_customer_payment()), [waiting])
        self.pay(ready)
        self.assertEqual(list(jobs_ready_for_payout()), [])

    def test_earnings_figures(self):
        a = self.pay(self.make_job())
        self.make_job()
        self.make_job(pay_invoice=False)
        self.pay(self.make_job(), labour_amount=Decimal('1000.00'), materials_amount=Decimal('0'))
        a.confirm(self.handyman)
        e = handyman_earnings(self.handyman)
        self.assertEqual(e['paid_this_month'], Decimal('9850.00'))
        self.assertEqual(e['confirmed_total'], Decimal('8850.00'))
        self.assertEqual(e['waiting_confirmation'], Decimal('1000.00'))
        self.assertEqual((e['ready_for_payout'], e['waiting_for_customer']), (1, 1))

    def test_other_handymen_do_not_see_each_others_figures(self):
        self.pay(self.make_job())
        self.assertEqual(handyman_earnings(self.other_handyman)['paid_this_month'], Decimal('0.00'))


class PayoutViewTests(PayoutBase):
    def login(self, user):
        self.client.force_login(user)

    def test_access_by_role(self):
        self.assertEqual(self.client.get(reverse('payments:payout_list')).status_code, 302)
        self.login(self.customer)
        self.assertEqual(self.client.get(reverse('payments:payout_list')).status_code, 403)
        self.login(self.handyman)
        self.assertEqual(self.client.get(reverse('payments:payout_list')).status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse('payments:my_earnings')).status_code, 403)

    def test_admin_list_and_record_form(self):
        job = self.make_job()
        self.login(self.admin)
        self.assertContains(self.client.get(reverse('payments:payout_list')), job.reference)
        page = self.client.get(reverse('payments:payout_record', args=[job.pk]))
        self.assertContains(page, '8000.00')
        self.assertContains(page, 'Customer paid MUR 12900.00')

    def test_admin_records_through_the_form(self):
        job = self.make_job()
        self.login(self.admin)
        r = self.client.post(reverse('payments:payout_record', args=[job.pk]), {
            'labour_amount': '8000.00', 'materials_amount': '850.00', 'date_paid': timezone.localdate().isoformat(),
            'method': 'cash', 'reference': 'X'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(HandymanPayout.objects.get().amount, Decimal('8850.00'))

    def test_form_shows_the_rule_error_and_saves_nothing(self):
        job = self.make_job()
        self.login(self.admin)
        r = self.client.post(reverse('payments:payout_record', args=[job.pk]), {
            'labour_amount': '99999.00', 'materials_amount': '0', 'date_paid': timezone.localdate().isoformat(), 'method': 'cash'})
        self.assertContains(r, 'more than the customer paid')
        self.assertEqual(HandymanPayout.objects.count(), 0)

    def test_record_page_refuses_a_job_that_is_not_ready(self):
        job = self.make_job(pay_invoice=False)
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse('payments:payout_record', args=[job.pk])).status_code, 302)

    def test_handyman_earnings_page_and_confirm(self):
        p = self.pay(self.make_job())
        self.login(self.handyman)
        page = self.client.get(reverse('payments:my_earnings'))
        self.assertContains(page, p.number)
        self.assertContains(page, 'Please confirm')
        r = self.client.post(reverse('payments:payout_confirm', args=[p.pk]), {'proof_image': image()})
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.status, 'confirmed')
        self.assertTrue(p.proof_image)

    def test_a_handyman_cannot_open_or_confirm_another_handymans_payout(self):
        p = self.pay(self.make_job())
        self.login(self.other_handyman)
        self.assertEqual(self.client.get(reverse('payments:payout_detail', args=[p.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('payments:payout_confirm', args=[p.pk])).status_code, 404)

    def test_admin_detail_shows_the_cross_check(self):
        p = self.pay(self.make_job(), labour_amount=Decimal('9000.00'))
        self.login(self.admin)
        page = self.client.get(reverse('payments:payout_detail', args=[p.pk]))
        self.assertContains(page, 'Platform margin')
        self.assertContains(page, 'differs from the approved estimate')
        self.login(self.handyman)
        self.assertNotContains(self.client.get(reverse('payments:payout_detail', args=[p.pk])), 'Platform margin')
