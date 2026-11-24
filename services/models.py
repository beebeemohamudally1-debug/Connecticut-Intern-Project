from django.db import models
from django.db.models import Q


class ServiceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True, category__is_active=True)

    def search(self, term):
        term = (term or '').strip()
        if not term:
            return self
        return self.filter(
            Q(name__icontains=term)
            | Q(description__icontains=term)
            | Q(category__name__icontains=term)
        )


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'service categories'

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='services')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        ordering = ['category__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['category', 'name'], name='unique_service_per_category'),
        ]

    def __str__(self):
        return f'{self.category.name} - {self.name}'


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(
        ServiceCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='skills'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ServiceArea(models.Model):
    """The nine regions. Used for handyman coverage and for a customer's residential region."""
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
