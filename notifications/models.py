
from django.conf import settings
from django.db import models


class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ('service_request', 'New Service Request'),
        ('quotation', 'Quotation Update'),
        ('job', 'Job Update'),
        ('complaint', 'Complaint'),
        ('feedback', 'Customer Feedback'),
        ('other', 'Other'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default='other'
    )

    title = models.CharField(max_length=150)

    message = models.TextField()
    url = models.CharField(
    max_length=500,
    blank=True,
    default=''
)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

