
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .services import notify_admins

from .models import Notification


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
            reverse('notification_list')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()['notifications']), 1
        )

    def test_unread_count(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('unread_count')
        )

        self.assertEqual(
            response.json()['unread_count'], 1
        )

    def test_mark_as_read(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                'mark_as_read',
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
            reverse('mark_all_as_read')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.admin_user,
                is_read=False
            ).count(),
            0
        )

    def test_customer_cannot_view_notifications(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse('notification_list')
        )

        self.assertEqual(response.status_code, 403)

    def test_other_admin_cannot_read_notification(self):
        self.client.force_login(self.other_admin)

        response = self.client.post(
            reverse(
                'mark_as_read',
                args=[self.notification.id]
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_access(self):
        response = self.client.get(
            reverse('notification_list')
        )

        self.assertEqual(response.status_code, 302)

    def test_get_cannot_mark_notification_read(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                'mark_as_read',
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
