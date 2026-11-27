
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .services import notify_admins, notify_user
from bookings.models import ServiceRequest
from django.db import transaction
from .models import Notification
from complaints.models import Complaint
from complaints.signals import complaint_submitted
from notifications.models import Notification


User = get_user_model()


class NotificationTests(TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.customer = User.objects.create_user(
            username='customer_test',
            password='TestPass123!',
            role='customer'
        )

        self.other_admin = User.objects.create_user(
            username='other_admin',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.notification = Notification.objects.create(
            recipient=self.admin_user,
            notification_type='service_request',
            title='New Service Request',
            message='A customer submitted a request.'
        )

    def test_notification_created(self):
        self.assertEqual(
            Notification.objects.count(), 1
        )
        self.assertFalse(self.notification.is_read)

    def test_admin_can_view_notifications(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('notifications:notification_list')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()['notifications']), 1
        )

    def test_unread_count(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('notifications:unread_count')
        )

        self.assertEqual(
            response.json()['unread_count'], 1
        )

    def test_mark_as_read(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                'notifications:mark_as_read',
                args=[self.notification.id]
            )
        )

        self.notification.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.notification.is_read)

    def test_mark_all_as_read(self):
        self.client.force_login(self.admin_user)

        Notification.objects.create(
            recipient=self.admin_user,
            title='Second Notification',
            message='Another event.'
        )

        response = self.client.post(
            reverse('notifications:mark_all_as_read')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.admin_user,
                is_read=False
            ).count(),
            0
        )

    def test_customer_can_view_own_notifications(self):
        notification = notify_user(
            recipient=self.customer,
            notification_type='quotation',
            title='New Quotation',
            message='Your quotation is ready.'
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse('notifications:notification_list')
        )

        self.assertEqual(response.status_code, 200)

        notifications = response.json()['notifications']

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['id'], notification.id)

    def test_other_admin_cannot_read_notification(self):
        self.client.force_login(self.other_admin)

        response = self.client.post(
            reverse(
                'notifications:mark_as_read',
                args=[self.notification.id]
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_access(self):
        response = self.client.get(
            reverse('notifications:notification_list')
        )

        self.assertEqual(response.status_code, 302)

    def test_get_cannot_mark_notification_read(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                'notifications:mark_as_read',
                args=[self.notification.id]
            )
        )

        self.assertEqual(response.status_code, 405)

        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)


    def test_notify_all_admins(self):
        notifications = notify_admins(
            notification_type='service_request',
            title='New Service Request',
            message='A new request has been submitted.'
        )

        self.assertEqual(len(notifications), 2)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin_user,
                title='New Service Request'
            ).exists()
        )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.other_admin,
                title='New Service Request'
            ).exists()
        )

    def test_customer_does_not_receive_admin_notification(self):
        notify_admins(
            notification_type='complaint',
            title='New Complaint',
            message='A complaint was submitted.'
        )

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.customer
            ).exists()
        )

    def test_inactive_admin_does_not_receive_notification(self):
        self.other_admin.is_active = False
        self.other_admin.save(update_fields=['is_active'])

        notifications = notify_admins(
            notification_type='job',
            title='Job Completed',
            message='A handyman completed a job.'
        )

        self.assertEqual(len(notifications), 1)
        self.assertEqual(
            notifications[0].recipient_id,
            self.admin_user.id
        )

    def test_superuser_can_access_notifications(self):
        superuser = User.objects.create_superuser(
            username='superuser_test',
            password='TestPass123!'
        )

        self.client.force_login(superuser)

        response = self.client.get(
            reverse('notifications:notification_list')
        )

        self.assertEqual(response.status_code, 200)

    def test_handyman_can_view_own_notifications(self):
        handyman = User.objects.create_user(
            username='handyman_test',
            password='TestPass123!',
            role='handyman'
        )

        notification = notify_user(
            recipient=handyman,
            notification_type='job',
            title='New Job Assigned',
            message='You have been assigned a new job.'
        )

        self.client.force_login(handyman)

        response = self.client.get(
            reverse('notifications:notification_list')
        )

        self.assertEqual(response.status_code, 200)
        notifications = response.json()['notifications']

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['id'], notification.id)

    def test_customer_cannot_read_admin_notification(self):
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse(
                'notifications:mark_as_read',
                args=[self.notification.id]
            )
        )

        self.assertEqual(response.status_code, 404)

        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_customer_mark_all_only_affects_own_notifications(self):
        notification = notify_user(
            recipient=self.customer,
            notification_type='quotation',
            title='New Quotation',
            message='Your quotation is ready.'
        )

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('notifications:mark_all_as_read')
        )

        self.assertEqual(response.status_code, 200)

        notification.refresh_from_db()
        self.notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertFalse(self.notification.is_read)

    def test_inactive_user_does_not_receive_notification(self):
        self.customer.is_active = False
        self.customer.save(update_fields=['is_active'])

        notification = notify_user(
            recipient=self.customer,
            notification_type='job',
            title='Job Update',
            message='Your job has been updated.'
        )

        self.assertIsNone(notification)


class ComplaintNotificationSignalTests(TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='complaint_admin_test',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.other_admin = User.objects.create_user(
            username='complaint_other_admin',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.customer = User.objects.create_user(
            username='complaint_customer_test',
            password='TestPass123!',
            role='customer'
        )

    def test_complaint_submission_notifies_admins(self):
        complaint = Complaint(
            pk=123,
            reference='CMP-123'
        )

        with self.captureOnCommitCallbacks(execute=True):
            complaint_submitted.send(
                sender=Complaint,
                complaint=complaint
            )

        notifications = Notification.objects.filter(
            title='New Complaint Submitted'
        )

        self.assertEqual(notifications.count(), 2)

        expected_url = reverse(
            'complaints:detail',
            kwargs={'pk': 123}
        )

        for notification in notifications:
            self.assertEqual(notification.url, expected_url)
            self.assertFalse(notification.is_read)

        self.assertEqual(
            set(notifications.values_list('recipient_id', flat=True)),
            {self.admin_user.pk, self.other_admin.pk}
        )

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.customer
            ).exists()
        )


class ServiceRequestNotificationSignalTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username='service_admin_test',
            password='TestPass123!',
            role='admin',
            is_staff=True
        )

        self.customer = User.objects.create_user(
            username='service_customer_test',
            password='TestPass123!',
            role='customer'
        )

    def test_new_service_request_notifies_admin(self):
        with self.captureOnCommitCallbacks(execute=True):
            service_request = ServiceRequest.objects.create(
                customer=self.customer,
                service_category='Plumbing',
                problem_description='Leaking kitchen tap',
                status='requested'
            )

        notifications = Notification.objects.filter(
            notification_type='service_request'
        )

        self.assertEqual(notifications.count(), 1)

        notification = notifications.first()

        self.assertEqual(notification.recipient, self.admin)
        self.assertEqual(notification.title, 'New Service Request')
        self.assertIn(service_request.reference, notification.message)
        self.assertIn('Plumbing', notification.message)
        self.assertFalse(notification.is_read)

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.customer
            ).exists()
        )

    def test_updating_service_request_does_not_notify_again(self):
        with self.captureOnCommitCallbacks(execute=True):
            service_request = ServiceRequest.objects.create(
                customer=self.customer,
                service_category='Electrical',
                status='requested'
            )

        self.assertEqual(
            Notification.objects.filter(
                notification_type='service_request'
            ).count(),
            1
        )

        with self.captureOnCommitCallbacks(execute=True):
            service_request.status = ServiceRequest.STATUS_REVIEWING
            service_request.save()

        self.assertEqual(
            Notification.objects.filter(
                notification_type='service_request'
            ).count(),
            1
        )

    def test_cancelled_request_does_not_notify_admin(self):
        with self.captureOnCommitCallbacks(execute=True):
            ServiceRequest.objects.create(
                customer=self.customer,
                service_category='Cleaning',
                status=ServiceRequest.STATUS_CANCELLED
            )

        self.assertFalse(
            Notification.objects.filter(
                notification_type='service_request'
            ).exists()
        )

    def test_rolled_back_request_does_not_notify_admin(self):
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    ServiceRequest.objects.create(
                        customer=self.customer,
                        service_category='Painting',
                        status='requested'
                    )
                    raise ValueError('Simulated rollback')
            except ValueError:
                pass

        self.assertFalse(
            Notification.objects.filter(
                notification_type='service_request'
            ).exists()
        )
