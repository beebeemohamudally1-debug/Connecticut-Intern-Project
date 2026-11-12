from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from jobs.models import Job
from .models import Complaint, ComplaintLog, ComplaintMessage
from .signals import complaint_submitted

User = get_user_model()


class ComplaintTests(TestCase):
    def setUp(self):
        mk = User.objects.create_user
        self.admin = mk('admin1', password='x', role='admin', is_staff=True)
        self.customer = mk('cust1', password='x', role='customer')
        self.other_customer = mk('cust2', password='x', role='customer')
        self.handyman = mk('hand1', password='x', role='handyman')
        self.job = Job.objects.create(
            customer=self.customer, handyman=self.handyman, service_name='Plumbing',
            description='Leaking tap', address='12 Royal Road')
        self.other_job = Job.objects.create(
            customer=self.other_customer, handyman=self.handyman, service_name='Painting',
            description='Walls', address='x')

    def login(self, user):
        self.client.force_login(user)

    def url(self, name, *args):
        return reverse(f'complaints:{name}', args=args)

    def make(self, by=None, job=None):
        by = by or self.customer
        job = job or self.job
        c = Complaint.objects.create(
            submitted_by=by, job=job, subject='Late', description='Arrived late',
            against=job.handyman if by == job.customer else job.customer)
        ComplaintLog.objects.create(complaint=c, actor=by, to_status=Complaint.PENDING)
        return c

    def test_customer_files_complaint_against_handyman(self):
        received = []
        complaint_submitted.connect(lambda sender, complaint, **kw: received.append(complaint),
                                    weak=False, dispatch_uid='t_sub')
        self.login(self.customer)
        res = self.client.post(self.url('create'), {
            'job': self.job.pk, 'subject': 'Late', 'description': 'Two hours late'})
        complaint_submitted.disconnect(dispatch_uid='t_sub')
        c = Complaint.objects.get()
        self.assertRedirects(res, self.url('detail', c.pk))
        self.assertEqual(c.submitted_by, self.customer)
        self.assertEqual(c.against, self.handyman)
        self.assertEqual(c.status, Complaint.PENDING)
        self.assertTrue(c.reference.startswith('CMP-'))
        self.assertEqual(c.log.count(), 1)
        self.assertEqual(len(received), 1)

    def test_handyman_files_complaint_against_customer(self):
        self.login(self.handyman)
        self.client.post(self.url('create'), {
            'job': self.job.pk, 'subject': 'No access', 'description': 'Nobody home'})
        self.assertEqual(Complaint.objects.get().against, self.customer)

    def test_cannot_file_on_someone_elses_job(self):
        self.login(self.customer)
        self.client.post(self.url('create'), {
            'job': self.other_job.pk, 'subject': 'x', 'description': 'y'})
        self.assertFalse(Complaint.objects.exists())

    def test_admin_cannot_use_customer_form(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(self.url('create')).status_code, 403)

    def test_visibility(self):
        c = self.make()
        self.login(self.customer)
        self.assertEqual(self.client.get(self.url('detail', c.pk)).status_code, 200)
        self.login(self.handyman)  # named in the complaint
        self.assertEqual(self.client.get(self.url('detail', c.pk)).status_code, 200)
        self.login(self.other_customer)
        self.assertEqual(self.client.get(self.url('detail', c.pk)).status_code, 404)
        self.login(self.admin)
        self.assertEqual(self.client.get(self.url('detail', c.pk)).status_code, 200)

    def test_party_lists_show_only_their_complaints(self):
        self.make()
        self.login(self.other_customer)
        self.assertEqual(len(self.client.get(self.url('list')).context['complaints']), 0)
        self.login(self.admin)
        self.assertEqual(len(self.client.get(self.url('list')).context['complaints']), 1)

    def test_admin_enquiry_moves_to_in_progress_and_is_private_to_recipient(self):
        c = self.make()
        self.login(self.admin)
        self.client.post(self.url('enquiry', c.pk), {
            'recipient': str(self.handyman.pk), 'body': 'Why were you late?'})
        c.refresh_from_db()
        self.assertEqual(c.status, Complaint.IN_PROGRESS)
        self.assertEqual(c.log.count(), 2)
        self.login(self.handyman)
        self.assertEqual(len(self.client.get(self.url('detail', c.pk)).context['thread']), 1)
        self.login(self.customer)
        self.assertEqual(len(self.client.get(self.url('detail', c.pk)).context['thread']), 0)

    def test_enquiry_recipient_must_be_a_party(self):
        c = self.make()
        self.login(self.admin)
        self.client.post(self.url('enquiry', c.pk), {
            'recipient': str(self.other_customer.pk), 'body': 'Hi'})
        self.assertFalse(ComplaintMessage.objects.exists())

    def test_party_reply_visible_to_admin_not_to_other_party(self):
        c = self.make()
        self.login(self.handyman)
        self.client.post(self.url('reply', c.pk), {'body': 'Traffic on the motorway'})
        self.assertEqual(c.messages.filter(kind='response').count(), 1)
        self.login(self.customer)
        self.assertEqual(len(self.client.get(self.url('detail', c.pk)).context['thread']), 0)
        self.login(self.admin)
        self.assertEqual(len(self.client.get(self.url('detail', c.pk)).context['thread']), 1)

    def test_resolving_needs_outcome(self):
        c = self.make()
        self.login(self.admin)
        self.client.post(self.url('resolution', c.pk), {'status': 'resolved', 'outcome': ''})
        c.refresh_from_db()
        self.assertEqual(c.status, Complaint.PENDING)
        self.client.post(self.url('resolution', c.pk), {'status': 'resolved', 'outcome': 'Warning issued'})
        c.refresh_from_db()
        self.assertEqual(c.status, Complaint.RESOLVED)
        self.assertEqual(c.resolved_by, self.admin)
        self.assertIsNotNone(c.resolved_at)
        self.assertEqual(c.outcome, 'Warning issued')

    def test_resolved_complaint_is_locked(self):
        c = self.make()
        self.login(self.admin)
        self.client.post(self.url('resolution', c.pk), {'status': 'resolved', 'outcome': 'Done'})
        self.client.post(self.url('resolution', c.pk), {'status': 'in_progress', 'outcome': 'Changed'})
        c.refresh_from_db()
        self.assertEqual(c.status, Complaint.RESOLVED)
        self.assertEqual(c.outcome, 'Done')
        self.client.post(self.url('enquiry', c.pk), {'recipient': str(self.customer.pk), 'body': 'x'})
        self.assertFalse(ComplaintMessage.objects.exists())
        self.login(self.customer)
        self.client.post(self.url('reply', c.pk), {'body': 'late reply'})
        self.assertFalse(ComplaintMessage.objects.exists())

    def test_non_admin_cannot_resolve(self):
        c = self.make()
        self.login(self.customer)
        res = self.client.post(self.url('resolution', c.pk), {'status': 'resolved', 'outcome': 'x'})
        self.assertEqual(res.status_code, 403)

    def test_admin_list_filters(self):
        self.make()
        self.make(by=self.handyman)
        self.login(self.admin)
        res = self.client.get(self.url('list') + '?by=handyman')
        self.assertEqual(len(res.context['complaints']), 1)
        res = self.client.get(self.url('list') + '?status=resolved')
        self.assertEqual(len(res.context['complaints']), 0)
