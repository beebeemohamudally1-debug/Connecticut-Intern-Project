from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from jobs.models import Job
from complaints.models import Complaint
from bookings.models import ServiceRequest
from datetime import timedelta
from django.utils import timezone
from bookings.models import Appointment
from payments.models import Quotation, Payment
from decimal import Decimal

from .permissions import role_required
from .services import get_admin_dashboard_stats


User = get_user_model()


class DashboardTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.customer = User.objects.create_user(
            username='test_customer',
            password='TestPass123!',
            role='customer'
        )

        self.handyman = User.objects.create_user(
            username='test_handyman',
            password='TestPass123!',
            role='handyman'
        )

        self.admin_user = User.objects.create_user(
            username='test_admin',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

    def test_customer_access(self):
        @role_required('customer')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.customer

        self.assertEqual(test_view(request).status_code, 200)

    def test_handyman_access(self):
        @role_required('handyman')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.handyman

        self.assertEqual(test_view(request).status_code, 200)

    def test_admin_access(self):
        @role_required('admin')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.admin_user

        self.assertEqual(test_view(request).status_code, 200)

    def test_customer_cannot_access_admin(self):
        @role_required('admin')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = self.customer

        self.assertEqual(test_view(request).status_code, 403)

    def test_dashboard_counts(self):
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_customers'], 1)
        self.assertEqual(stats['total_handymen'], 1)
        self.assertEqual(stats['total_admins'], 1)

    def test_inactive_users_not_counted(self):
        User.objects.create_user(
            username='inactive_customer',
            password='TestPass123!',
            role='customer',
            is_active=False
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_customers'], 1)

    def test_non_staff_admin_role_denied(self):
        user = User.objects.create_user(
            username='fake_admin',
            password='TestPass123!',
            role='admin',
            is_staff=False
        )

        @role_required('admin')
        def test_view(request):
            return JsonResponse({'success': True})

        request = self.factory.get('/')
        request.user = user

        response = test_view(request)

        self.assertEqual(response.status_code, 403)


    def test_job_statistics(self):
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_jobs'], 0)
        self.assertEqual(stats['assigned_jobs'], 0)
        self.assertEqual(stats['in_progress_jobs'], 0)
        self.assertEqual(stats['completed_jobs'], 0)
        self.assertEqual(stats['cancelled_jobs'], 0)


    def test_complaint_statistics(self):
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_complaints'], 0)
        self.assertEqual(stats['pending_complaints'], 0)
        self.assertEqual(stats['in_progress_complaints'], 0)
        self.assertEqual(stats['resolved_complaints'], 0)

    
    def test_job_statistics_with_records(self):
        Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Plumbing',
            description='Fix leaking pipe',
            address='Test Address',
            status=Job.ASSIGNED
        )

        Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Electrical',
            description='Repair light',
            address='Test Address',
            status=Job.COMPLETED
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_jobs'], 2)
        self.assertEqual(stats['assigned_jobs'], 1)
        self.assertEqual(stats['completed_jobs'], 1)
        self.assertEqual(stats['in_progress_jobs'], 0)
        self.assertEqual(stats['cancelled_jobs'], 0)


    def test_complaint_statistics_with_records(self):
        job = Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Plumbing',
            description='Fix leaking pipe',
            address='Test Address',
            status=Job.COMPLETED
        )

        Complaint.objects.create(
            submitted_by=self.customer,
            against=self.handyman,
            job=job,
            subject='Poor workmanship',
            description='The pipe is still leaking.',
            status=Complaint.PENDING
        )

        Complaint.objects.create(
            submitted_by=self.customer,
            against=self.handyman,
            job=job,
            subject='Delayed service',
            description='The repair was delayed.',
            status=Complaint.IN_PROGRESS
        )

        Complaint.objects.create(
            submitted_by=self.customer,
            against=self.handyman,
            job=job,
            subject='Service issue',
            description='The issue has been addressed.',
            status=Complaint.RESOLVED,
            outcome='Complaint investigated and resolved.'
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_complaints'], 3)
        self.assertEqual(stats['pending_complaints'], 1)
        self.assertEqual(stats['in_progress_complaints'], 1)
        self.assertEqual(stats['resolved_complaints'], 1)


    def test_booking_statistics_with_records(self):
        ServiceRequest.objects.create(
            customer=self.customer,
            service_category='Plumbing',
            problem_description='Leaking pipe',
            status='requested'
        )

        ServiceRequest.objects.create(
            customer=self.customer,
            service_category='Electrical',
            problem_description='Broken light',
            status=ServiceRequest.STATUS_REVIEWING
        )

        ServiceRequest.objects.create(
            customer=self.customer,
            service_category='Painting',
            problem_description='Paint bedroom',
            status=ServiceRequest.STATUS_BOOKED
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_service_requests'], 3)
        self.assertEqual(stats['new_service_requests'], 1)
        self.assertEqual(stats['reviewing_requests'], 1)
        self.assertEqual(stats['booked_requests'], 1)


    def test_appointment_statistics_with_records(self):
        service_request = ServiceRequest.objects.create(
            customer=self.customer,
            service_category='Plumbing',
            problem_description='Leaking pipe'
        )

        Appointment.objects.create(
            service_request=service_request,
            handyman=self.handyman,
            appointment_date=timezone.localdate() + timedelta(days=2),
            time_slot='morning',
            status=Appointment.STATUS_CONFIRMED
        )

        Appointment.objects.create(
            service_request=service_request,
            handyman=self.handyman,
            appointment_date=timezone.localdate() + timedelta(days=3),
            time_slot='afternoon',
            status=Appointment.STATUS_PENDING
        )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_appointments'], 2)
        self.assertEqual(stats['pending_appointments'], 1)
        self.assertEqual(stats['confirmed_appointments'], 1)
        self.assertEqual(stats['upcoming_appointments'], 1)


    def test_quotation_statistics_with_records(self):
        statuses = [
            Quotation.DRAFT,
            Quotation.SENT,
            Quotation.ACCEPTED,
            Quotation.DECLINED,
        ]

        for index, status in enumerate(statuses):
            service_request = ServiceRequest.objects.create(
                customer=self.customer,
                service_category='Plumbing',
                problem_description=f'Test problem {index}'
            )

            Quotation.objects.create(
                request=service_request,
                work_description='Plumbing repair',
                total_amount=Decimal('1500.00'),
                status=status,
                created_by=self.admin_user
            )

        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['total_quotations'], 4)
        self.assertEqual(stats['draft_quotations'], 1)
        self.assertEqual(stats['sent_quotations'], 1)
        self.assertEqual(stats['accepted_quotations'], 1)
        self.assertEqual(stats['declined_quotations'], 1)
        self.assertEqual(stats['awaiting_payment'], 1)
        self.assertEqual(stats['total_payments'], 0)


    def test_payment_statistics_with_records(self):
        service_request = ServiceRequest.objects.create(
            customer=self.customer,
            service_category='Plumbing',
            problem_description='Fix leaking pipe'
        )

        quotation = Quotation.objects.create(
            request=service_request,
            work_description='Plumbing repair',
            total_amount=Decimal('2500.00'),
            status=Quotation.ACCEPTED,
            created_by=self.admin_user
        )

        # Before payment
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['awaiting_payment'], 1)
        self.assertEqual(stats['total_payments'], 0)
        self.assertEqual(stats['total_amount_received'], 0)

        # Administrator records full offline payment
        Payment.objects.create(
            quotation=quotation,
            amount=Decimal('2500.00'),
            date_received=timezone.localdate(),
            method='cash',
            recorded_by=self.admin_user
        )

        # After payment
        stats = get_admin_dashboard_stats()

        self.assertEqual(stats['awaiting_payment'], 0)
        self.assertEqual(stats['total_payments'], 1)
        self.assertEqual(
            stats['total_amount_received'],
            Decimal('2500.00')
        )
