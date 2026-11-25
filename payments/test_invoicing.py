import re
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import ServiceRequest

from .models import Invoice, Quotation

User = get_user_model()
PASSWORD = 'pw12345!'


def make_user(username, role):
    # ADAPT if your user model needs more fields than username, password and role
    return User.objects.create_user(username=username, password=PASSWORD, role=role)


def make_service_request(customer):
    # ADAPT: create a ServiceRequest with whatever fields your model requires
    return ServiceRequest.objects.create(customer=customer)


def make_quotation(service_request, admin, kind, amount, status=Quotation.ACCEPTED):
    return Quotation.objects.create(
        request=service_request, quotation_type=kind, work_description=f'{kind} work',
        total_amount=Decimal(amount), status=status, created_by=admin, responded_at=timezone.now())


class InvoiceFlowTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin1', 'admin')
        self.customer = make_user('cust1', 'customer')
        self.other = make_user('cust2', 'customer')
        self.req = make_service_request(self.customer)
        self.labour = make_quotation(self.req, self.admin, Quotation.LABOUR, '11000.00')
        self.material = make_quotation(self.req, self.admin, Quotation.MATERIAL, '1500.00')
        self.due = timezone.localdate() + timedelta(days=5)

    def issue(self):
        return Invoice.issue_job(self.admin, self.req, self.due)

    # ---- issuing
    def test_job_invoice_totals_and_number(self):
        invoice = self.issue()
        self.assertEqual(invoice.total_amount, Decimal('12500.00'))
        self.assertRegex(invoice.number, r'^INV-\d{4}-0001$')

    def test_numbers_do_not_repeat(self):
        first = self.issue()
        first.cancel(self.admin)
        second = self.issue()
        self.assertNotEqual(first.number, second.number)
        self.assertTrue(second.number.endswith('0002'))

    def test_cannot_issue_without_accepted_labour(self):
        self.labour.status = Quotation.SENT
        self.labour.save()
        with self.assertRaises(ValidationError):
            self.issue()

    def test_cannot_issue_twice(self):
        self.issue()
        with self.assertRaises(ValidationError):
            self.issue()

    def test_only_admin_can_issue(self):
        with self.assertRaises(ValidationError):
            Invoice.issue_job(self.customer, self.req, self.due)

    def test_inspection_invoice(self):
        invoice = Invoice.issue_inspection(self.admin, self.req, self.due, 'Possible hidden damage')
        self.assertRegex(invoice.number, r'^INS-\d{4}-0001$')
        self.assertEqual(invoice.total_amount, Decimal('500.00'))

    # ---- paying
    def pay(self, invoice, amount, clear, received=True):
        return invoice.record_payment(self.admin, amount=Decimal(amount), date_received=timezone.localdate(),
                                      method='bank_transfer', reference='TRF-1', received=received, clear=clear)

    def test_cannot_clear_partial_amount(self):
        invoice = self.issue()
        with self.assertRaises(ValidationError):
            self.pay(invoice, '5000.00', clear=True)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.ISSUED)

    def test_save_without_clearing_then_clear(self):
        invoice = self.issue()
        self.pay(invoice, '5000.00', clear=False)
        self.pay(invoice, '12500.00', clear=True)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.PAID)

    def test_clearing_creates_receipt_and_keeps_old_payment_ledger_in_step(self):
        invoice = self.issue()
        self.pay(invoice, '12500.00', clear=True)
        self.assertRegex(invoice.receipt.number, r'^RCT-\d{4}-0001$')
        self.labour.refresh_from_db()
        self.material.refresh_from_db()
        self.assertTrue(self.labour.is_paid and self.material.is_paid)   # what bookings.Appointment relies on

    def test_cannot_pay_a_paid_invoice_again(self):
        invoice = self.issue()
        self.pay(invoice, '12500.00', clear=True)
        with self.assertRaises(ValidationError):
            self.pay(invoice, '12500.00', clear=True)

    # ---- pages
    def test_admin_pages_load(self):
        invoice = self.issue()
        self.client.login(username='admin1', password=PASSWORD)
        for name, args in [('invoice_list', []), ('invoice_issue', [self.req.pk]),
                           ('inspection_invoice_issue', [self.req.pk]), ('invoice_record_payment', [invoice.pk])]:
            response = self.client.get(reverse(f'payments:{name}', args=args))
            self.assertEqual(response.status_code, 200, name)

    def test_issue_invoice_through_the_page(self):
        self.client.login(username='admin1', password=PASSWORD)
        response = self.client.post(reverse('payments:invoice_issue', args=[self.req.pk]), {
            'due_date': self.due.isoformat(), 'payment_instructions': 'Pay by bank transfer.'})
        self.assertRedirects(response, reverse('payments:invoice_list'))
        self.assertEqual(Invoice.objects.count(), 1)

    def test_customer_sees_own_invoice_and_receipt_only(self):
        invoice = self.issue()
        self.pay(invoice, '12500.00', clear=True)
        self.client.login(username='cust1', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('payments:my_invoices')).status_code, 200)
        self.assertEqual(self.client.get(reverse('payments:invoice_detail', args=[invoice.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('payments:receipt_detail', args=[invoice.receipt.pk])).status_code, 200)
        self.client.login(username='cust2', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('payments:invoice_detail', args=[invoice.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('payments:receipt_detail', args=[invoice.receipt.pk])).status_code, 404)

    def test_customer_cannot_open_admin_pages(self):
        self.client.login(username='cust1', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('payments:invoice_list')).status_code, 403)


class DeadLinkTests(TestCase):
    """Logs in as each role, opens the main pages, follows every internal link on them and
    reports any that answer 404 or 500. Read the failure message: it names the page and the link."""

    START = {
        'admin': ['payments:invoice_list', 'payments:quotation_list', 'payments:estimate_list',
                  'payments:admin_materials', 'payments:material_quotation_list'],
        'customer': ['payments:my_invoices', 'payments:my_quotations', 'payments:payment_history'],
        'handyman': ['payments:my_estimates', 'payments:my_materials'],
    }
    SKIP = ('/static/', '/media/', 'logout', 'mailto:', 'tel:')

    def test_no_dead_links(self):
        problems = []
        for role, names in self.START.items():
            make_user(f'{role}_x', role)
            self.client.login(username=f'{role}_x', password=PASSWORD)
            seen = set()
            for name in names:
                page = reverse(name)
                html = self.client.get(page).content.decode(errors='ignore')
                for href in set(re.findall(r'href="(/[^"#?]*)', html)):
                    if href in seen or any(s in href for s in self.SKIP):
                        continue
                    seen.add(href)
                    status = self.client.get(href).status_code
                    if status in (404, 500):
                        problems.append(f'{role}: {href}  ->  {status}   (found on {page})')
        self.assertEqual(problems, [], '\n' + '\n'.join(problems))
