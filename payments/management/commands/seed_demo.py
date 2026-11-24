"""Fill the local database with demo data for the admin pages (Service Quotations, payments,
materials, Private Feedback, Job Summary, Complaints, Work Progress, Manage Users and Appointments).

Run:      python manage.py seed_demo
Start over: python manage.py seed_demo --reset

Only for local testing. Every demo user starts with "demo_", so the data is easy to find
and remove. It prints the links to open at the end.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils import timezone

from bookings.models import Appointment, HandymanProfileRequest, ServiceRequest, ServiceRequestAssignment
from complaints.models import Complaint, ComplaintEvidence, ComplaintLog, ComplaintMessage
from jobs.models import Job, ProgressReport, TimeLog, WorkEvidence
from reviews.models import Review
from payments.models import LabourEstimate, MaterialPurchaseRequest, MaterialReceipt, Payment, Quotation

User = get_user_model()
BASE = 'http://127.0.0.1:8000'


# Demo skills for Manage Skills: name, category (a trade), active. Skills are what a handyman can do;
# the bookable tasks are the services of the services app, so the names differ from those.
DEMO_SKILLS = [
    ('Pipe fitting', 'Plumbing', True), ('Water heater maintenance', 'Plumbing', True),
    ('Leak detection', 'Plumbing', True), ('Drain inspection', 'Plumbing', True),
    ('Circuit testing', 'Electrical', True), ('House wiring', 'Electrical', True),
    ('Fault finding', 'Electrical', True), ('Lock fitting', 'Carpentry', True),
    ('Wood joinery', 'Carpentry', True), ('Spray painting', 'Painting', True),
    ('Wall preparation', 'Painting', False), ('Plant care', 'Gardening', True),
    ('Refrigerant handling', 'Air conditioning', True),
    ('Appliance diagnostics', 'Appliance repair', False), ('Roof waterproofing', None, False),
]
# Names used by an older version of this command, deleted by --reset
OLD_DEMO_SKILLS = ['Pipe installation', 'Water heater repair', 'Bathroom plumbing', 'Drain cleaning',
                   'Electrical repair', 'Electrical wiring', 'Light fitting', 'Door fitting',
                   'Furniture assembly', 'Painting', 'Wall plastering', 'Lawn care',
                   'Air conditioner servicing', 'Washing machine repair', 'Roof repair']

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
    def user(self, username, role, first, last, phone='', active=True):
        # The admin portal pages also need is_staff (dashboard.permissions.role_required)
        u, made = User.objects.get_or_create(
            username=username, defaults={'role': role, 'first_name': first, 'last_name': last,
                                         'email': f'{username}@example.com', 'is_staff': role == 'admin',
                                         'phone': phone, 'is_active': active})
        if made:
            u.set_password('demo12345')
            u.save()
        return u

    def reset(self):
        demo = {'request__customer__username__startswith': 'demo_'}
        Payment.objects.filter(quotation__request__customer__username__startswith='demo_').delete()
        MaterialReceipt.objects.filter(purchase_request__request__customer__username__startswith='demo_').delete()
        MaterialPurchaseRequest.objects.filter(**demo).delete()
        Quotation.objects.filter(**demo).delete()
        LabourEstimate.objects.filter(**demo).delete()
        demo_complaints = Complaint.objects.filter(submitted_by__username__startswith='demo_')
        ComplaintLog.objects.filter(complaint__in=demo_complaints).delete()
        ComplaintEvidence.objects.filter(complaint__in=demo_complaints).delete()
        ComplaintMessage.objects.filter(complaint__in=demo_complaints).delete()
        demo_complaints.delete()
        Review.objects.filter(customer__username__startswith='demo_').delete()
        Job.objects.filter(customer__username__startswith='demo_').delete()
        Appointment.objects.filter(service_request__customer__username__startswith='demo_').delete()
        ServiceRequestAssignment.objects.filter(service_request__customer__username__startswith='demo_').delete()
        HandymanProfileRequest.objects.filter(handyman__username__startswith='demo_').delete()
        ServiceRequest.objects.filter(customer__username__startswith='demo_').delete()
        User.objects.filter(username__startswith='demo_').delete()
        try:   # demo skills (Manage Skills), including the names used by older versions of this command
            from services.models import Skill
            Skill.objects.filter(name__in=[n for n, _, _ in DEMO_SKILLS] + OLD_DEMO_SKILLS).delete()
        except ImportError:
            pass
        self.stdout.write('Old demo data deleted.')

    # ------------------------------------------------------------------- create
    def create(self):
        admin = self.user('demo_admin', 'admin', 'Demo', 'Admin')
        customers = [self.user('demo_aisha', 'customer', 'Aisha', 'Khan', '5 712 3344'),
                     self.user('demo_priya', 'customer', 'Priya', 'Nair', '5 845 1209'),
                     self.user('demo_david', 'customer', 'David', 'Park', '5 903 6672'),
                     self.user('demo_sarah', 'customer', 'Sarah', 'Thompson', '5 987 6543')]
        handymen = [self.user('demo_marcus', 'handyman', 'Marcus', 'Reed', '5 731 1145'),
                    self.user('demo_alex', 'handyman', 'Alex', 'Smith', '5 644 2091')]
        # Manage Users: suspended accounts (is_active = False) and approved skills / services
        self.user('demo_daniel', 'customer', 'Daniel', 'Brooks', '5 412 7788', active=False)
        self.user('demo_jean', 'handyman', 'Jean', 'Laval', '5 220 4810', active=False)
        self.profile_requests(admin, handymen)
        self.skills(handymen)

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
        # One receipt approved, one waiting for review.
        self.material(admin, handymen[0], 'accepted', '4 fence panels\n2 posts\n1 tin of wood paint', '3200', paid=False,
                      receipts=[('1850', 'approved'), ('1250', 'submitted')])
        # Water heater: both accepted and both paid (whole request paid, appointment can be scheduled).
        self.material(admin, handymen[1], 'paid', '1 heating element\n1 thermostat', '1900', paid=True,
                      receipts=[('1150', 'approved'), ('690', 'approved')])
        # Material Quotations: one request in every other stage
        MaterialPurchaseRequest.objects.create(
            request_id=self.ids['changes_requested']['request'], handyman=handymen[1],
            items='3 tins of wall paint (5 L)\n2 paint rollers\n1 roll of masking tape', estimated_cost=Decimal('2150'))
        MaterialPurchaseRequest.objects.create(
            request_id=self.ids['needs_quote']['request'], handyman=handymen[1], items='1 pressure pump\n4 m copper pipe',
            estimated_cost=Decimal('6500'), status=MaterialPurchaseRequest.REJECTED, reviewed_by=admin,
            reviewed_at=timezone.now(), admin_note='A new pump is not needed for this repair. Please send the pipe only.')
        self.material(admin, handymen[0], 'changes_requested_2', '2 tins of deck stain (4 L)\n1 sanding pack', '2400', status='sent')
        self.material(admin, handymen[1], 'changes_requested_3', '1 bathroom extractor fan\n1 m vent duct\n1 wall grille', '1750',
                      status='revision_requested', note='The fan looks expensive. Is there a cheaper model?')
        self.material(admin, handymen[0], 'declined', '2 gutter brackets\n1 tube of sealant', '780', status='declined')
        self.material(admin, handymen[0], 'sent', '1 ceiling fan\n1 mounting bracket', '3400')

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
        review_jobs = []
        for c, h, service, rating, status, comment, days_ago in reviews:
            when = timezone.now() - timedelta(days=days_ago)
            job = Job.objects.create(customer=customers[c], handyman=handymen[h], service_name=service,
                                     description=f'Demo job: {service}.', address='12 Royal Road, Port Louis',
                                     status=Job.COMPLETED, completed_at=when - timedelta(hours=3),
                                     scheduled_start=when - timedelta(days=1))
            Job.objects.filter(pk=job.pk).update(created_at=when - timedelta(days=5))
            review_jobs.append(job)
            review = Review.objects.create(job=job, customer=customers[c], rating=rating, comment=comment)
            done = status != 'pending'
            Review.objects.filter(pk=review.pk).update(
                created_at=when, status=status, assessed_by=admin if done else None,
                assessed_at=when + timedelta(days=1) if done else None)

        # Jobs for the Job Summary report (created after the review jobs, so they are listed first), linked to the requests above so the report shows
        # the accepted quotation amount and the payment status.
        now = timezone.now()
        report_jobs = {}
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
            report_jobs[key] = job

        self.complaints(admin, review_jobs)
        self.work_progress(admin, customers, handymen, report_jobs)
        self.appointments(admin, handymen)
        self.service_requests(admin, customers, handymen)

    def service_requests(self, admin, customers, handymen):
        """Manage Service Requests: requests in every stage (new, forwarded, rejected, cancelled)."""
        rows = [
            # (service, customer, handyman or None, request status, answer, handyman's note, date, slot, address, problem)
            ('Bathroom plumbing', 3, None, 'submitted', None, '', 27, 'morning', 'Quatre Bornes',
             'Leaking tap and damaged pipe connection beneath the bathroom sink.'),
            ('Tap replacement', 0, None, 'reviewing', None, '', 28, 'afternoon', 'Rose Hill',
             'Kitchen mixer tap is loose and drips constantly.'),
            ('Electrical repair', 1, 0, 'assigned', 'sent', '', 29, 'morning', 'Curepipe',
             'Two sockets in the living room stopped working.'),
            ('Carpentry', 2, 1, 'assigned', 'rejected', 'Unavailable on the requested date.', 26, 'afternoon', 'Vacoas',
             'Wardrobe door hinge is broken and the door does not close.'),
            ('Curtain rail fitting', 1, None, 'cancelled', None, '', 24, 'morning', 'Moka',
             'Fit two curtain rails in the bedroom.'),
        ]
        for service, c, h, status, answer, note, day, slot, town, problem in rows:
            req = ServiceRequest.objects.create(
                customer=customers[c], service_category=service, problem_description=problem,
                service_address=f'{town}, Mauritius', contact_name=customers[c].get_full_name(),
                contact_phone=customers[c].phone, preferred_date=date(2026, 11, day), preferred_slot=slot, status=status)
            if h is not None:
                ServiceRequestAssignment.objects.create(
                    service_request=req, handyman=handymen[h], status=answer, sent_by=admin, response_note=note,
                    responded_at=timezone.now() if answer != 'sent' else None)

    def complaints(self, admin, jobs):
        """Demo complaints in every status, with private messages, a photo and a status log."""
        now = timezone.now()

        def make(job, by_customer, subject, description, days_ago):
            filer, other = (job.customer, job.handyman) if by_customer else (job.handyman, job.customer)
            c = Complaint.objects.create(submitted_by=filer, against=other, job=job,
                                         subject=subject, description=description)
            when = now - timedelta(days=days_ago)
            Complaint.objects.filter(pk=c.pk).update(created_at=when)
            c.created_at = when   # keep it when the status is saved later
            log = ComplaintLog.objects.create(complaint=c, actor=filer, to_status=Complaint.PENDING,
                                              note='Complaint submitted')
            ComplaintLog.objects.filter(pk=log.pk).update(created_at=when)
            return c, when

        def say(c, author, body, when, recipient=None):
            kind = ComplaintMessage.ENQUIRY if recipient else ComplaintMessage.RESPONSE
            m = ComplaintMessage.objects.create(complaint=c, author=author, recipient=recipient, kind=kind, body=body)
            ComplaintMessage.objects.filter(pk=m.pk).update(created_at=when)

        def move(c, to, when, note, outcome=''):
            ComplaintLog.objects.filter(pk=ComplaintLog.objects.create(
                complaint=c, actor=admin, from_status=c.status, to_status=to, note=note).pk).update(created_at=when)
            c.status = to
            if outcome:
                c.outcome, c.resolved_by, c.resolved_at = outcome, admin, when
            c.save()

        # Pending: nobody has looked yet
        make(jobs[2], True, 'Door still squeaks',
             'The hinge was replaced but the door still squeaks when it closes. The handyman also arrived an hour late.', 2)
        make(jobs[3], False, 'Customer was not home',
             'I arrived at the agreed time but nobody was home, and the customer did not answer the phone.', 1)

        # In progress: enquiries sent, one person replied, with a photo
        c, when = make(jobs[0], True, 'Cabinet still damp',
                       'The sink no longer leaks, but the cabinet floor still feels damp. Could someone check it is safe?', 6)
        say(c, admin, 'Thanks for letting us know. Is there fresh water under the sink, or is the wood damp from before? A photo would help.',
            when + timedelta(hours=2), recipient=c.submitted_by)
        say(c, admin, 'We are looking into a moisture concern after the sink repair. Was the cabinet dry when you finished?',
            when + timedelta(hours=2, minutes=5), recipient=c.against)
        move(c, Complaint.IN_PROGRESS, when + timedelta(hours=2), 'Enquiry sent')
        say(c, c.submitted_by, 'There is no fresh drip. The wood feels damp near the back. I have attached a photo.',
            when + timedelta(hours=5))
        ComplaintEvidence.objects.create(complaint=c, uploaded_by=c.submitted_by,
                                         file=ContentFile(b'%PDF-1.4 demo photo', name='cabinet-moisture.pdf'))

        # Resolved: both replied, outcome recorded
        c, when = make(jobs[1], True, 'Paint marks on the floor',
                       'There are paint marks on the wooden floor near the wall that was painted.', 12)
        say(c, admin, 'Could you send a photo of the marks and tell us how large they are?', when + timedelta(hours=3),
            recipient=c.submitted_by)
        say(c, admin, 'The customer reports paint marks on the floor. Was the floor covered while you worked?',
            when + timedelta(hours=3, minutes=10), recipient=c.against)
        move(c, Complaint.IN_PROGRESS, when + timedelta(hours=3), 'Enquiry sent')
        say(c, c.submitted_by, 'Three small marks near the skirting board, each about the size of a coin.', when + timedelta(hours=6))
        say(c, c.against, 'The floor was covered, but one sheet moved. I can come back and clean it at no charge.',
            when + timedelta(hours=8))
        move(c, Complaint.RESOLVED, when + timedelta(days=2), 'Outcome recorded',
             outcome='The handyman returned at no charge and removed the paint marks. The customer confirmed the floor is clean.')

    def appointments(self, admin, handymen):
        """Inspection and service appointments in every status, around today, with one booking clash."""
        today = timezone.localdate()
        A = Appointment
        rows = [
            # key, type, handyman, days from today, slot, status, note
            ('paid', A.TYPE_SERVICE, 1, 2, 'morning', A.STATUS_CONFIRMED, 'The handyman will call 30 minutes before arriving.'),
            ('needs_review_3', A.TYPE_INSPECTION, 1, 2, 'morning', A.STATUS_PENDING, ''),          # clashes with the one above
            ('needs_review', A.TYPE_INSPECTION, 0, 1, 'afternoon', A.STATUS_PENDING, ''),
            ('estimate_revision', A.TYPE_INSPECTION, 0, 5, 'morning', A.STATUS_CONFIRMED, ''),
            ('sent', A.TYPE_INSPECTION, 1, 8, 'afternoon', A.STATUS_CONFIRMED, ''),
            ('needs_review_2', A.TYPE_INSPECTION, 1, 0, 'afternoon', A.STATUS_CONFIRMED, ''),
            ('accepted_waiting', A.TYPE_INSPECTION, 0, -6, 'morning', A.STATUS_COMPLETED, ''),
            ('needs_quote', A.TYPE_INSPECTION, 1, -3, 'afternoon', A.STATUS_COMPLETED, ''),
            ('declined', A.TYPE_INSPECTION, 0, -1, 'morning', A.STATUS_CANCELLED, 'Customer was away.'),
            ('changes_requested', A.TYPE_INSPECTION, 1, -2, 'morning', A.STATUS_PENDING, ''),  # date passed, never confirmed
        ]
        for key, kind, h, days, slot, status, note in rows:
            done = status in (A.STATUS_CONFIRMED, A.STATUS_COMPLETED)
            A.objects.create(service_request_id=self.ids[key]['request'], handyman=handymen[h], appointment_type=kind,
                             appointment_date=today + timedelta(days=days), time_slot=slot, status=status, notes=note,
                             confirmed_by=admin if done else None, confirmed_at=timezone.now() if done else None)

    def profile_requests(self, admin, handymen):
        """Skills and services for the Handyman Profile (approved, pending and rejected changes)."""
        now = timezone.now()
        H = HandymanProfileRequest
        rows = [
            (0, H.TYPE_SKILL, H.ACTION_ADD, '', 'Pipe fitting', H.STATUS_APPROVED, 30),
            (0, H.TYPE_SKILL, H.ACTION_ADD, '', 'Water heater maintenance', H.STATUS_APPROVED, 29),
            (0, H.TYPE_SKILL, H.ACTION_ADD, '', 'Leak detection', H.STATUS_APPROVED, 28),
            (0, H.TYPE_SERVICE, H.ACTION_ADD, '', 'Pipe leak repair', H.STATUS_APPROVED, 28),
            (0, H.TYPE_SERVICE, H.ACTION_ADD, '', 'Tap replacement', H.STATUS_APPROVED, 27),
            (0, H.TYPE_SERVICE, H.ACTION_MODIFY, 'Tap replacement', 'Tap and mixer replacement', H.STATUS_APPROVED, 10),
            (0, H.TYPE_SERVICE, H.ACTION_ADD, '', 'Gate repair', H.STATUS_APPROVED, 8),
            (0, H.TYPE_SKILL, H.ACTION_ADD, '', 'Roof waterproofing', H.STATUS_PENDING, 2),
            (1, H.TYPE_SKILL, H.ACTION_ADD, '', 'Circuit testing', H.STATUS_APPROVED, 25),
            (1, H.TYPE_SKILL, H.ACTION_ADD, '', 'Spray painting', H.STATUS_APPROVED, 24),
            (1, H.TYPE_SERVICE, H.ACTION_ADD, '', 'Light fitting', H.STATUS_APPROVED, 24),
            (1, H.TYPE_SERVICE, H.ACTION_ADD, '', 'Wall painting', H.STATUS_APPROVED, 23),
            (1, H.TYPE_SERVICE, H.ACTION_ADD, '', 'Gas fitting', H.STATUS_REJECTED, 12),
        ]
        for h, kind, action, current, requested, status, days in rows:
            done = status != H.STATUS_PENDING
            r = H.objects.create(handyman=handymen[h], request_type=kind, action=action, current_value=current,
                                 requested_value=requested, status=status,
                                 reviewed_by=admin if done else None,
                                 reviewed_at=now - timedelta(days=days - 1) if done else None)
            H.objects.filter(pk=r.pk).update(submitted_at=now - timedelta(days=days))   # auto_now_add

    def skills(self, handymen):
        """Skill catalogue, handyman profiles and extra skill requests (Manage Skills pages).
        Needs the services app and accounts.HandymanProfile (services PR); skipped without them."""
        try:
            from accounts.models import HandymanProfile
            from services.models import ServiceArea, ServiceCategory, Skill
        except ImportError:
            return
        skill = {}
        for name, cat, active in DEMO_SKILLS:
            category = ServiceCategory.objects.filter(name=cat).first() if cat else None
            obj, _ = Skill.objects.update_or_create(name=name, defaults={'category': category, 'is_active': active})
            skill[name] = obj
        jean = User.objects.get(username='demo_jean')
        profiles = [
            (handymen[0], HandymanProfile.STATUS_ACTIVE, ['Pipe fitting', 'Water heater maintenance', 'Leak detection']),
            (handymen[1], HandymanProfile.STATUS_ACTIVE, ['Circuit testing', 'Spray painting', 'Fault finding']),
            (jean, HandymanProfile.STATUS_PENDING, ['Leak detection', 'House wiring']),
        ]
        areas = {a.name: a for a in ServiceArea.objects.all()}
        coverage = {handymen[0]: ['Port Louis', 'Moka'], handymen[1]: ['Plaines Wilhems'], jean: ['Flacq']}
        for user, status, names in profiles:
            profile = HandymanProfile.objects.create(user=user, status=status)
            profile.skills.set([skill[n] for n in names])
            profile.service_areas.set([areas[a] for a in coverage[user] if a in areas])
            User.objects.filter(pk=user.pk).update(region=areas.get(coverage[user][0]))

        H = HandymanProfileRequest
        now = timezone.now()
        rows = [   # handyman, action, current, requested, status, days ago, reason, admin note
            (handymen[1], H.ACTION_ADD, '', 'House wiring', H.STATUS_PENDING, 1,
             'Five years of house wiring work and a valid electrician licence.', ''),
            (handymen[0], H.ACTION_MODIFY, 'Water heater maintenance', 'Solar heater maintenance', H.STATUS_PENDING, 3,
             'Most of my water heater jobs are now solar systems.', ''),
            (handymen[1], H.ACTION_REMOVE, 'Spray painting', '', H.STATUS_PENDING, 4,
             'I no longer do spray painting.', ''),
            (handymen[0], H.ACTION_ADD, '', 'Drain inspection', H.STATUS_REJECTED, 15,
             'I can inspect drains with a camera.', 'Please upload proof of drain inspection work first.'),
        ]
        for h, action, current, requested, status, days, reason, note in rows:
            done = status != H.STATUS_PENDING
            r = H.objects.create(handyman=h, request_type=H.TYPE_SKILL, action=action, current_value=current,
                                 requested_value=requested, reason=reason, status=status, admin_note=note,
                                 reviewed_at=now - timedelta(days=days - 1) if done else None)
            H.objects.filter(pk=r.pk).update(submitted_at=now - timedelta(days=days))   # auto_now_add

    def work_progress(self, admin, customers, handymen, report_jobs):
        """Arrival times, daily reports and photos for Monitor Work Progress,
        with one delayed job and one flagged job."""
        today = timezone.localdate()

        def at(days_ago, hour, minute=0):
            return timezone.make_aware(datetime.combine(today - timedelta(days=days_ago), time(hour, minute)))

        def arrive(job, days_ago, out=True):
            TimeLog.objects.create(job=job, arrived_at=at(days_ago, 9),
                                   clocked_out_at=at(days_ago, 16) if out else None)

        def report(job, days_ago, percent, details, photos=()):
            r = ProgressReport.objects.create(job=job, author=job.handyman, report_date=today - timedelta(days=days_ago),
                                              details=details, percent_complete=percent)
            ProgressReport.objects.filter(pk=r.pk).update(updated_at=at(days_ago, 16, 30))
            for i, caption in enumerate(photos, 1):
                ev = WorkEvidence.objects.create(job=job, uploaded_by=job.handyman, caption=caption,
                                                 image=self.photo(f'{job.reference.lower()}_{days_ago}_{i}.png', i))
                WorkEvidence.objects.filter(pk=ev.pk).update(uploaded_at=at(days_ago, 16, 10 + i))

        # Delayed: due 2 days ago and still in progress (waiting for a part)
        late = Job.objects.create(customer=customers[0], handyman=handymen[0], service_name='Plumbing',
                                  description='Kitchen pipe repair and replacement', address='12 Royal Road, Port Louis',
                                  status=Job.IN_PROGRESS, scheduled_start=at(6, 9), due_date=today - timedelta(days=2))
        Job.objects.filter(pk=late.pk).update(created_at=at(8, 10, 30))
        arrive(late, 6)
        report(late, 6, 10, 'Met the customer on site, confirmed the work and photographed the damaged pipe.',
               ['Damaged pipe before work'])
        report(late, 5, 35, 'Turned off the water and removed the damaged pipe section. Site ready for the new pipes.',
               ['Old pipe removed', 'Water supply isolated'])
        report(late, 4, 65, 'New supply pipes fitted and joints tightened. First leak check passed.',
               ['Pipework overview', 'New supply connection', 'Under-sink joint', 'Leak check'])
        report(late, 2, 65, 'Waiting for a replacement elbow fitting before the final pressure test.',
               ['Missing fitting'])

        # Flagged: on time, but the latest photo does not match the report
        flagged = Job.objects.create(customer=customers[1], handyman=handymen[1], service_name='Electrical',
                                     description='Living room rewiring', address='5 Rue Pope Hennessy, Curepipe',
                                     status=Job.IN_PROGRESS, scheduled_start=at(3, 9), due_date=today + timedelta(days=2),
                                     is_flagged=True, flagged_by=admin, flagged_at=at(0, 9, 15),
                                     flag_reason='The photo uploaded yesterday shows a different room from the one in the report.')
        Job.objects.filter(pk=flagged.pk).update(created_at=at(5, 11))
        arrive(flagged, 3)
        report(flagged, 3, 30, 'Old wiring traced and the circuit switched off. Started removing old sockets.',
               ['Old socket removed'])
        report(flagged, 1, 50, 'New cables run along the living room wall. Sockets fitted on one side.',
               ['New sockets fitted'])

        # On time and in progress (Wall painting)
        job = report_jobs['changes_requested']
        Job.objects.filter(pk=job.pk).update(due_date=today + timedelta(days=3))
        arrive(job, 1)
        report(job, 1, 40, 'Walls washed, cracks filled and sanded. Masking done around the windows.',
               ['Walls prepared', 'Cracks filled'])
        arrive(job, 0, out=False)
        report(job, 0, 55, 'First coat applied to two walls.', ['First coat'])

        # Completed (Water heater service)
        job = report_jobs['paid']
        Job.objects.filter(pk=job.pk).update(due_date=today - timedelta(days=5),
                                             completion_notes='Old element replaced and thermostat set to 60°C. '
                                                              'The tank was refilled and tested; no leaks.')
        arrive(job, 6)
        report(job, 6, 50, 'Drained the tank and removed the old heating element.', ['Tank drained'])
        report(job, 5, 100, 'New element and thermostat fitted. Tank refilled and tested.',
               ['New element fitted', 'Thermostat set'])

        # Assigned, not started yet
        for key, days in [('accepted', 4), ('accepted_waiting', 6)]:
            Job.objects.filter(pk=report_jobs[key].pk).update(due_date=today + timedelta(days=days))

    def receipt_image(self, name, amount):
        """A small image that looks like a shop receipt."""
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (300, 420), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((24, 22), 'HARDWARE STORE LTD', fill=(40, 50, 70))
        for y in range(70, 300, 28):
            d.line([24, y, 200, y], fill=(170, 180, 195), width=3)
            d.line([230, y, 276, y], fill=(170, 180, 195), width=3)
        d.line([24, 330, 276, 330], fill=(40, 50, 70), width=2)
        d.text((24, 350), f'TOTAL  MUR {amount}', fill=(40, 50, 70))
        buf = BytesIO()
        img.save(buf, 'PNG')
        return ContentFile(buf.getvalue(), name=name)

    def photo(self, name, n):
        """A small plain image to stand in for a site photograph."""
        from PIL import Image, ImageDraw
        colours = [(203, 221, 240), (226, 214, 196), (210, 228, 214), (232, 215, 222)]
        img = Image.new('RGB', (480, 320), colours[(n - 1) % len(colours)])
        d = ImageDraw.Draw(img)
        d.rectangle([60, 70, 420, 250], outline=(70, 90, 120), width=6)
        d.line([60, 250, 200, 140, 300, 210, 360, 160, 420, 250], fill=(70, 90, 120), width=6)
        d.ellipse([320, 95, 370, 145], fill=(240, 170, 80))
        buf = BytesIO()
        img.save(buf, 'PNG')
        return ContentFile(buf.getvalue(), name=name)

    def material(self, admin, handyman, key, items, cost, paid=False, status='accepted', note='', receipts=()):
        """A purchase request forwarded as a material quotation, then answered by the customer."""
        mat = MaterialPurchaseRequest.objects.create(
            request_id=self.ids[key]['request'], handyman=handyman, items=items, estimated_cost=Decimal(cost))
        q = mat.forward(admin)
        if status != 'sent':
            q.status, q.responded_at, q.customer_note = status, timezone.now(), note
            q.save()
        for i, (amount, state) in enumerate(receipts, 1):
            MaterialReceipt.objects.create(
                purchase_request=mat, uploaded_by=handyman, amount_spent=Decimal(amount), status=state,
                image=self.receipt_image(f'demo_receipt_{mat.pk}_{i}.png', amount),
                reviewed_by=admin if state != 'submitted' else None,
                reviewed_at=timezone.now() if state != 'submitted' else None)
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
        out(f'  Work progress:     {BASE}/admin-portal/work-progress/')
        out(f'  Manage users:      {BASE}/admin-portal/users/')
        out(f'  Appointments:      {BASE}/admin-portal/appointments/')
        out(f'  Service requests:  {BASE}/bookings/admin/requests/')
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
        late = Job.objects.filter(customer__username__startswith='demo_', is_flagged=False,
                                  description='Kitchen pipe repair and replacement').first()
        if late:
            out('\nWork progress (delayed job)')
            out(f'  Job progress:      {BASE}/admin-portal/work-progress/{late.pk}/')
            out(f'  Daily reports:     {BASE}/admin-portal/work-progress/{late.pk}/reports/')
            out(f'  Evidence:          {BASE}/admin-portal/work-progress/{late.pk}/evidence/')
        out('')