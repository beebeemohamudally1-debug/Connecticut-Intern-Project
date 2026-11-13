
from django.db import transaction
from django.dispatch import receiver
from django.urls import reverse

from complaints.signals import complaint_submitted
from .services import notify_admins


@receiver(complaint_submitted, dispatch_uid='notify_admins_complaint_submitted')
def notify_on_complaint_submitted(sender, complaint, **kwargs):
    complaint_reference = complaint.reference
    complaint_url = reverse(
        'complaints:detail',
        kwargs={'pk': complaint.pk}
    )

    def create_notification():
        notify_admins(
            notification_type='complaint',
            title='New Complaint Submitted',
            message=f'Complaint {complaint_reference} has been submitted.',
            url=complaint_url
        )

    transaction.on_commit(create_notification)
