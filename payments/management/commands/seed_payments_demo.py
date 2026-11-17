"""Fill the local database with demo data for the payment and quotation pages.

Run:      python manage.py seed_payments_demo
Start over: python manage.py seed_payments_demo --reset

Only for local testing. Every demo user starts with "demo_", so the data is easy to find
and remove. It prints the links to open at the end.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from bookings.models import ServiceRequest, ServiceRequestAssignment
from payments.models import LabourEstimate, MaterialPurchaseRequest, Payment, Quotation

User = get_user_model()
BASE = 'http://127.0.0.1:8000'


class Command(BaseCommand):
    help = 'Create demo data for the payment and quotation pages (local testing only).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete the demo data first.')

    def handle(self, *args, **options):
        if options['reset']:
            self.reset()
        if ServiceRequest.objects.filter(customer__username__startswith='demo_').exists():
            self.stdout.write('Demo data already exists. Use --reset to create it again.\n')
            self.print_links()
            return
        with transaction.atomic():
            self.create()
        self.stdout.write(self.style.SUCCESS('Demo data created.\n'))
        self.print_links()

    # ------------------------------------------------------------------ helpers
    def user(self, username, role, first, last):
        # The admin portal pages also need is_staff (dashboard.permissions.role_required)
        u, made = User.objects.get_or_create(
            username=username, defaults={'role': role, 'first_name': first, 'last_name': last,
                                         'email': f'{username}@example.com', 'is_staff': role == 'admin'})
        if made:
            u.set_password('demo12345')
            u.save()
        return u

    def reset(self):
        demo = {'request__customer__username__startswith': 'demo_'}
        Payment.objects.filter(quotation__request__customer__username__startswith='demo_').delete()
        MaterialPurchaseRequest.objects.filter(**demo).delete()
        Quotation.objects.filter(**demo).delete()
        LabourEstimate.objects.filter(**demo).delete()
        ServiceRequestAssignment.objects.filter(service_request__customer__username__startswith='demo_').delete()
        ServiceRequest.objects.filter(customer__username__startswith='demo_').delete()
        User.objects.filter(username__startswith='demo_').delete()
        self.stdout.write('Old demo data deleted.')

    # ------------------------------------------------------------------- create
    def create(self):
        admin = self.user('demo_admin', 'admin', 'Demo', 'Admin')
        customers = [self.user('demo_aisha', 'customer', 'Aisha', 'Khan'),
                     self.user('demo_priya', 'customer', 'Priya', 'Nair'),
                     self.user('demo_david', 'customer', 'David', 'Park'),
                     self.user('demo_sarah', 'customer', 'Sarah', 'Thompson')]
        handymen = [self.user('demo_marcus', 'handyman', 'Marcus', 'Reed'),
                    self.user('demo_alex', 'handyman', 'Alex', 'Smith')]

        # (key, service, customer, handyman, labour, breakdown, estimate status, quotation status)
        rows = [
            ('needs_review', 'Bathroom tap replacement', 0, 0, '1800', 'Remove old tap\nFit new tap\nTest for leaks', 'submitted', None),
            ('needs_quote', 'Pipe leak repair', 0, 1, '4500', 'Repair leaking pipe\nReplace fittings\nPressure test', 'approved', None),
            ('estimate_revision', 'Door lock fitting', 1, 0, '2600', 'Fit new lock\nAdjust door', 'revision_requested', None),
            ('draft', 'Kitchen shelf install', 1, 1, '1500', 'Fix brackets\nMount two shelves', 'approved', 'draft'),
            ('sent', 'Ceiling fan installation', 1, 0, '2000', 'Mount fan\nConnect wiring\nTest speeds', 'approved', 'sent'),
            ('changes_requested', 'Wall painting', 2, 1, '6500', 'Prepare walls\nTwo coats of paint', 'approved', 'revision_requested'),
            ('accepted', 'Garden fence repair', 2, 0, '3000', 'Replace panels\nLevel posts\nPaint section', 'approved', 'accepted'),
            ('paid', 'Water heater service', 3, 1, '2400', 'Drain tank\nReplace element\nTest', 'approved', 'paid'),
            ('declined', 'Roof gutter cleaning', 3, 0, '5700', 'Clear gutters\nFlush downpipes', 'approved', 'declined'),
            ('cancelled', 'Shower installation', 0, 1, '4200', 'Remove old unit\nInstall shower\nSeal and test', 'approved', 'cancelled'),
        ]
        self.ids = {}
        for key, service, c, h, amount, breakdown, est_status, q_status in rows:
            req = ServiceRequest.objects.create(
                customer=customers[c], service_category=service, problem_description=f'Demo request: {service}.',
                service_address='12 Royal Road, Port Louis', contact_name=customers[c].get_full_name(),
                contact_phone='5 123 4567', preferred_date=date(2026, 11, 25), preferred_slot='morning',
                status='booked' if q_status == 'paid' else 'assigned')
            ServiceRequestAssignment.objects.create(service_request=req, handyman=handymen[h],
                                                    status='accepted', sent_by=admin)
            est = LabourEstimate.objects.create(
                request=req, handyman=handymen[h], amount=Decimal(amount), breakdown=breakdown, status=est_status,
                admin_note='Please split the cost per task.' if est_status == 'revision_requested' else '',
                reviewed_by=None if est_status == 'submitted' else admin,
                reviewed_at=None if est_status == 'submitted' else timezone.now())
            self.ids[key] = {'request': req.pk, 'estimate': est.pk}
            if not q_status:
                continue
            total = (Decimal(amount) * Decimal('1.15')).quantize(Decimal('1'))
            q = Quotation.objects.create(
                request=req, labour_estimate=est, work_description=breakdown, total_amount=total,
                status='accepted' if q_status == 'paid' else q_status, created_by=admin,
                customer_note='Could the price be lower? We can supply the paint.' if q_status == 'revision_requested' else '',
                responded_at=timezone.now() if q_status in ('accepted', 'paid', 'declined', 'revision_requested') else None)
            if q_status == 'paid':
                Payment.objects.create(quotation=q, amount=total, date_received=date(2026, 11, 15),
                                       method='bank_transfer', reference='DEMO-PAY-001', recorded_by=admin)
            self.ids[key]['quotation'] = q.pk

        # Materials: one waiting for review, one already forwarded as a material quotation
        MaterialPurchaseRequest.objects.create(
            request_id=self.ids['accepted']['request'], handyman=handymen[0],
            items='4 fence panels\n2 posts\n1 tin of wood paint', estimated_cost=Decimal('3200'))
        mat = MaterialPurchaseRequest.objects.create(
            request_id=self.ids['paid']['request'], handyman=handymen[1],
            items='1 heating element\n1 thermostat', estimated_cost=Decimal('1900'))
        mat.forward(admin)

    # -------------------------------------------------------------------- links
    def print_links(self):
        ids = {}
        for key, service in [('needs_quote', 'Pipe leak repair'), ('draft', 'Kitchen shelf install'),
                             ('sent', 'Ceiling fan installation'), ('changes_requested', 'Wall painting'),
                             ('accepted', 'Garden fence repair'), ('paid', 'Water heater service'),
                             ('declined', 'Roof gutter cleaning'), ('cancelled', 'Shower installation')]:
            req = ServiceRequest.objects.filter(customer__username__startswith='demo_', service_category=service).first()
            if not req:
                continue
            ids[key] = {'request': req.pk,
                        'estimate': getattr(req.labour_estimates.first(), 'pk', None),
                        'quotation': getattr(req.quotations.filter(quotation_type='labour').first(), 'pk', None)}
        out = self.stdout.write
        out('\nLists')
        out(f'  Labour estimates:  {BASE}/payments/estimates/')
        out(f'  Quotations:        {BASE}/payments/quotations/')
        out(f'  Materials:         {BASE}/payments/materials/')
        if 'needs_quote' in ids:
            i = ids['needs_quote']
            out('\nCreate quotation (from an approved estimate)')
            out(f'  {BASE}/payments/quotations/new/{i["request"]}/?estimate={i["estimate"]}')
        out('\nQuotation details')
        for key, label in [('draft', 'Draft'), ('sent', 'Sent, awaiting customer'), ('changes_requested', 'Changes requested'),
                           ('accepted', 'Accepted, unpaid'), ('paid', 'Paid'), ('declined', 'Declined'), ('cancelled', 'Cancelled')]:
            if key in ids and ids[key]['quotation']:
                out(f'  {label + ":":26} {BASE}/payments/quotations/{ids[key]["quotation"]}/')
        out('\nEdit / revise quotation')
        for key, label in [('draft', 'Edit draft'), ('changes_requested', 'Revise (customer asked)')]:
            if key in ids and ids[key]['quotation']:
                out(f'  {label + ":":26} {BASE}/payments/quotations/{ids[key]["quotation"]}/edit/')
        if 'accepted' in ids and ids['accepted']['quotation']:
            out('\nRecord payment (accepted quotation)')
            out(f'  {BASE}/payments/quotations/{ids["accepted"]["quotation"]}/pay/')
        out('')