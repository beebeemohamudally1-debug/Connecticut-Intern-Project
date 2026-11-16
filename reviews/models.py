from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from jobs.models import Job


class Review(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Pending Assessment'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    job = models.OneToOneField(
        Job,
        on_delete=models.PROTECT,
        related_name='review'
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='submitted_reviews'
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    comment = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assessed_reviews'
    )

    assessed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Review for {self.job.reference} - {self.rating}/5'

    def clean(self):
        super().clean()

        if self.job_id:
            if self.job.status != Job.COMPLETED:
                raise ValidationError({
                    'job': 'Only completed jobs can be reviewed.'
                })

            if self.customer_id != self.job.customer_id:
                raise ValidationError({
                    'customer': 'You can only review your own jobs.'
                })

        if self.customer_id and self.customer.role != 'customer':
            raise ValidationError({
                'customer': 'Only customers can submit reviews.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
