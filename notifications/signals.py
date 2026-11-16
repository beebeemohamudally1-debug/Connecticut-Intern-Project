
from django.db import transaction
from django.dispatch import receiver
from django.urls import reverse
from django.db.models.signals import post_save
from bookings.models import ServiceRequest

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


@receiver(
    post_save,
    sender=ServiceRequest,
    dispatch_uid='notify_admins_service_request_created'
)
def notify_on_service_request_created(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.status not in (
        ServiceRequest.STATUS_SUBMITTED,
        'requested'
    ):
        return

    
    request_id = instance.pk
    service_category = instance.service_category or 'General Service'

    def create_notification():
        service_request = ServiceRequest.objects.get(pk=request_id)

        reference = (
            service_request.reference
            or f'SR-{1000 + service_request.pk}'
        )

        notify_admins(
            notification_type='service_request',
            title='New Service Request',
            message=(
                f'Service request {reference} '
                f'for {service_category} has been received.'
            ),
            url=''
        )

    transaction.on_commit(create_notification)

