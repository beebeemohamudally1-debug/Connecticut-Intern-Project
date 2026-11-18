"""Fill the local database with demo data for the admin pages (Service Quotations, payments,
materials and Private Feedback).

Run:      python manage.py seed_demo
Start over: python manage.py seed_demo --reset

Only for local testing. Every demo user starts with "demo_", so the data is easy to find
and remove. It prints the links to open at the end.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from bookings.models import ServiceRequest, ServiceRequestAssignment
from jobs.models import Job
from reviews.models import Review
from payments.models import LabourEstimate, MaterialPurchaseRequest, Payment, Quotation

User = get_user_model()
BASE = 'http://127.0.0.1:8000'


class Command(BaseCommand):
    help = 'Create demo data for the admin pages (local testing only).'

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
        Review.objects.filter(customer__username__startswith='demo_').delete()
        Job.objects.filter(customer__username__startswith='demo_').delete()
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
            ('needs_review_2', 'Ceiling light fitting', 1, 1, '1200', 'Remove old fitting\nInstall new light\nTest switch', 'submitted', None),
            ('needs_review_3', 'Kitchen tap leak', 2, 0, '950', 'Replace washer\nTighten fittings', 'submitted', None),
            ('needs_review_4', 'Window latch repair', 3, 1, '700', 'Replace latch\nAdjust frame', 'submitted', None),
            ('estimate_revision_2', 'Tile regrouting', 3, 0, '3400', 'Remove old grout\nRegrout bathroom wall', 'revision_requested', None),
            ('needs_quote', 'Pipe leak repair', 0, 1, '4500', 'Repair leaking pipe\nReplace fittings\nPressure test', 'approved', None),
            ('estimate_revision', 'Door lock fitting', 1, 0, '2600', 'Fit new lock\nAdjust door', 'revision_requested', None),
            ('draft', 'Kitchen shelf install', 1, 1, '1500', 'Fix brackets\nMount two shelves', 'approved', 'draft'),
            ('sent', 'Ceiling fan installation', 1, 0, '2000', 'Mount fan\nConnect wiring\nTest speeds', 'approved', 'sent'),
            ('changes_requested', 'Wall painting', 2, 1, '6500', 'Prepare walls\nTwo coats of paint', 'approved', 'revision_requested'),
            ('changes_requested_2', 'Deck staining', 0, 0, '4800', 'Sand the deck\nApply two coats of stain', 'approved', 'revision_requested'),
            ('changes_requested_3', 'Bathroom fan install', 3, 1, '2200', 'Cut vent\nInstall fan\nConnect wiring', 'approved', 'revision_requested'),
            ('accepted', 'Garden fence repair', 2, 0, '3000', 'Replace panels\nLevel posts\nPaint section', 'approved', 'accepted'),
            ('accepted_waiting', 'Gate repair', 0, 0, '2800', 'Fix hinges\nRealign gate\nOil lock', 'approved', 'accepted'),
            ('paid', 'Water heater service', 3, 1, '2400', 'Drain tank\nReplace element\nTest', 'approved', 'paid'),
            ('declined', 'Roof gutter cleaning', 3, 0, '5700', 'Clear gutters\nFlush downpipes', 'approved', 'declined'),
            ('cancelled', 'Shower installation', 0, 1, '4200', 'Remove old unit\nInstall shower\nSeal and test', 'approved', 'cancelled'),
        ]
        # Rows without a quotation (estimates to review, quote or wait on) are created last,
        # so they show at the top of the lists (newest first).
        rows.sort(key=lambda r: r[7] is None)
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
                admin_note={'estimate_revision': 'Please split the cost per task.',
                            'estimate_revision_2': 'The labour cost looks high for one wall. Please check it.'}.get(key, '') if est_status == 'revision_requested' else '',
                reviewed_by=None if est_status == 'submitted' else admin,
                reviewed_at=None if est_status == 'submitted' else timezone.now())
            self.ids[key] = {'request': req.pk, 'estimate': est.pk}
            if not q_status:
                continue
            total = (Decimal(amount) * Decimal('1.15')).quantize(Decimal('1'))
            q = Quotation.objects.create(
                request=req, labour_estimate=est, work_description=breakdown, total_amount=total,
                status='accepted' if q_status == 'paid' else q_status, created_by=admin,
                customer_note={'changes_requested': 'Could the price be lower? We can supply the paint.',
                               'changes_requested_2': 'Please do one coat only, and finish before Friday.',
                               'changes_requested_3': 'Can you use the existing vent instead of cutting a new one?'}.get(key, '') if q_status == 'revision_requested' else '',
                responded_at=timezone.now() if q_status in ('accepted', 'paid', 'declined', 'revision_requested') else None)
            if q_status == 'paid':
                Payment.objects.create(quotation=q, amount=total, date_received=date(2026, 11, 15),
                                       method='bank_transfer', reference='DEMO-PAY-001', recorded_by=admin)
            self.ids[key]['quotation'] = q.pk

        # Materials (part B) and payment (part C): payment comes after BOTH quotations are accepted.
        # Gate repair: labour accepted, purchase request waiting for review (no material quotation yet).
        MaterialPurchaseRequest.objects.create(
            request_id=self.ids['accepted_waiting']['request'], handyman=handymen[0],
            items='2 gate hinges\n1 padlock', estimated_cost=Decimal('900'))
        # Garden fence: labour and material quotations both accepted, not paid yet (ready to pay).
        self.material(admin, handymen[0], 'accepted', '4 fence panels\n2 posts\n1 tin of wood paint', '3200', paid=False)
        # Water heater: both accepted and both paid (whole request paid, appointment can be scheduled).
        self.material(admin, handymen[1], 'paid', '1 heating element\n1 thermostat', '1900', paid=True)

        # Private feedback: completed jobs with customer reviews (pending, approved, rejected)
        reviews = [
            (0, 0, 'Kitchen sink leak repair', 4, 'pending', 'Marcus was friendly and explained the repair clearly. The cabinet could have been dried a little more thoroughly.', 2),
            (1, 1, 'Bedroom wall painting', 5, 'pending', 'Very good service and professional. The room looks brand new.', 4),
            (2, 0, 'Door hinge replacement', 2, 'pending', 'The door still squeaks a bit and the handyman arrived late.', 6),
            (3, 1, 'Bathroom tile repair', 5, 'pending', 'Satisfied with the work. Completed on time and left everything clean.', 9),
            (0, 1, 'Shelf installation', 4, 'approved', 'Good work, but could improve on cleanup.', 15),
            (2, 0, 'Light fitting', 5, 'approved', 'Quick and tidy. Would book again.', 25),
            (3, 0, 'Fence painting', 1, 'rejected', 'Terrible!!! call me now 5 999 9999', 40),
        ]
        for c, h, service, rating, status, comment, days_ago in reviews:
            when = timezone.now() - timedelta(days=days_ago)
            job = Job.objects.create(customer=customers[c], handyman=handymen[h], service_name=service,
                                     description=f'Demo job: {service}.', address='12 Royal Road, Port Louis',
                                     status=Job.COMPLETED, completed_at=when - timedelta(hours=3),
                                     scheduled_start=when - timedelta(days=1))
            Job.objects.filter(pk=job.pk).update(created_at=when - timedelta(days=5))
            review = Review.objects.create(job=job, customer=customers[c], rating=rating, comment=comment)
            done = status != 'pending'
            Review.objects.filter(pk=review.pk).update(
                created_at=when, status=status, assessed_by=admin if done else None,
                assessed_at=when + timedelta(days=1) if done else None)

        # Jobs for the Job Summary report (created after the review jobs, so they are listed first), linked to the requests above so the report shows
        # the accepted quotation amount and the payment status.
        now = timezone.now()
        for key, status, h, days in [('paid', Job.COMPLETED, 1, 6), ('accepted', Job.ASSIGNED, 0, -3),
                                     ('accepted_waiting', Job.ASSIGNED, 0, -5),
                                     ('changes_requested', Job.IN_PROGRESS, 1, -1),
                                     ('cancelled', Job.CANCELLED, 1, 2)]:
            req = ServiceRequest.objects.get(pk=self.ids[key]['request'])
            job = Job.objects.create(
                service_request=req, customer=req.customer, handyman=handymen[h],
                service_name=req.service_category, description=req.problem_description,
                address=req.service_address, status=status, scheduled_start=now - timedelta(days=days),
                completed_at=now - timedelta(days=days - 1) if status == Job.COMPLETED else None)
            # created_at is set automatically; move it back so the report's date filter has a spread
            Job.objects.filter(pk=job.pk).update(created_at=now - timedelta(days=abs(days) + 4))


    def material(self, admin, handyman, key, items, cost, paid):
        mat = MaterialPurchaseRequest.objects.create(
            request_id=self.ids[key]['request'], handyman=handyman, items=items, estimated_cost=Decimal(cost))
        q = mat.forward(admin)
        q.status, q.responded_at = 'accepted', timezone.now()
        q.save()
        if paid:
            Payment.objects.create(quotation=q, amount=q.total_amount, date_received=date(2026, 11, 15),
                                   method='bank_transfer', reference='DEMO-PAY-002', recorded_by=admin)

    # -------------------------------------------------------------------- links
    def print_links(self):
        ids = {}
        for key, service in [('needs_quote', 'Pipe leak repair'), ('draft', 'Kitchen shelf install'),
                             ('sent', 'Ceiling fan installation'), ('changes_requested', 'Wall painting'),
                             ('accepted', 'Garden fence repair'), ('accepted_waiting', 'Gate repair'),
                             ('paid', 'Water heater service'),
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
        out(f'  Private feedback:  {BASE}/reviews/admin/')
        if 'needs_quote' in ids:
            i = ids['needs_quote']
            out('\nCreate quotation (from an approved estimate)')
            out(f'  {BASE}/payments/quotations/new/{i["request"]}/?estimate={i["estimate"]}')
        out('\nQuotation details')
        for key, label in [('draft', 'Draft'), ('sent', 'Sent, awaiting customer'), ('changes_requested', 'Changes requested'),
                           ('accepted_waiting', 'Accepted, no materials'), ('accepted', 'Both accepted, unpaid'),
                           ('paid', 'Both paid'), ('declined', 'Declined'), ('cancelled', 'Cancelled')]:
            if key in ids and ids[key]['quotation']:
                out(f'  {label + ":":26} {BASE}/payments/quotations/{ids[key]["quotation"]}/')
        out('\nEdit / revise quotation')
        for key, label in [('draft', 'Edit draft'), ('changes_requested', 'Revise (customer asked)')]:
            if key in ids and ids[key]['quotation']:
                out(f'  {label + ":":26} {BASE}/payments/quotations/{ids[key]["quotation"]}/edit/')
        if 'accepted' in ids and ids['accepted']['quotation']:
            out('\nRecord payment (both quotations accepted)')
            out(f'  {BASE}/payments/quotations/{ids["accepted"]["quotation"]}/pay/')
        out('')