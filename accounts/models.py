from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

class User(AbstractUser):
    ROLE_CUSTOMER = 'customer'
    ROLE_HANDYMAN = 'handyman'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_HANDYMAN, 'Handyman'),
        (ROLE_ADMIN, 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)   # 8-digit rule is enforced in the forms, not here
    additional_names = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    region = models.ForeignKey(
        'services.ServiceArea', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='residents',
    )
    is_suspended = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)   # admin first login
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower('email'), condition=~Q(email=''), name='unique_user_email_ci',
            ),
        ]

    @property
    def is_customer(self):
        return self.role == self.ROLE_CUSTOMER

    @property
    def is_handyman(self):
        return self.role == self.ROLE_HANDYMAN


class HandymanProfile(models.Model):
    STATUS_PENDING = 'PENDING_APPROVAL'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending approval'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='handyman_profile', limit_choices_to={'role': 'handyman'},
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    categories = models.ManyToManyField('services.ServiceCategory', blank=True, related_name='handymen')
    services = models.ManyToManyField('services.Service', blank=True, related_name='handymen')
    skills = models.ManyToManyField('services.Skill', blank=True, related_name='handymen')
    service_areas = models.ManyToManyField('services.ServiceArea', blank=True, related_name='handymen')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} ({self.get_status_display()})'

    @property
    def is_approved(self):
        return self.status == self.STATUS_ACTIVE

    def clean(self):
        if self.user_id and self.user.role != User.ROLE_HANDYMAN:
            raise ValidationError({'user': 'The selected user is not a handyman.'})
        
class EmailVerification(models.Model):
    """One-time email codes for registration and password reset. Only a hash is stored."""
    PURPOSE_REGISTER = 'register'
    PURPOSE_RESET = 'reset'

    email = models.EmailField()
    purpose = models.CharField(max_length=10)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=['email', 'purpose', 'created_at'])]
        
class ProviderDocument(models.Model):
    """An ID photo or certificate uploaded by a handyman. Private: only administrators may view."""
    KIND_ID = 'id_photo'
    KIND_CERTIFICATE = 'certificate'
    KIND_CHOICES = [(KIND_ID, 'ID card photo'), (KIND_CERTIFICATE, 'Certificate')]

    profile = models.ForeignKey(HandymanProfile, on_delete=models.CASCADE, related_name='documents')
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    file = models.FileField(upload_to='handyman_documents/%Y/%m/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.profile} - {self.get_kind_display()}'