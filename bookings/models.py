#YOU MAY REMOVE THE CODE BELOW-IT WAS ONLY USED FOR TESTING PURPOSES

from django.conf import settings
from django.db import models

class ServiceRequest(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='requested')
