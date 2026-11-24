from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import HandymanProfile
from services.models import Service, ServiceArea, ServiceCategory


class ServiceSearchTests(TestCase):
    def test_search_by_name_and_category(self):
        self.assertTrue(Service.objects.search('leak').filter(name='Pipe leak repair').exists())
        self.assertTrue(Service.objects.search('Plumbing').filter(name='Tap replacement').exists())

    def test_inactive_service_hidden(self):
        s = Service.objects.get(name='Pipe leak repair')
        s.is_active = False
        s.save()
        self.assertFalse(Service.objects.active().filter(pk=s.pk).exists())


class HandymanLinkTests(TestCase):
    def test_handyman_linked_to_service_and_area(self):
        user = get_user_model().objects.create_user(
            username='hand1', email='hand1@example.com', password='Str0ngPass!word', role='handyman')
        profile = HandymanProfile.objects.create(user=user)
        service = Service.objects.get(name='Pipe leak repair')
        profile.services.add(service)
        profile.categories.add(ServiceCategory.objects.get(name='Plumbing'))
        profile.service_areas.add(ServiceArea.objects.get(name='Flacq'))
        self.assertTrue(service.handymen.filter(user=user).exists())
        self.assertEqual(profile.status, HandymanProfile.STATUS_PENDING)
# Create your tests here.
