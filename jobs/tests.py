import io
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Job, ProgressReport
from .signals import job_completed

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp()


def png_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), 'white').save(buf, 'PNG')
    return buf.getvalue()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class JobTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        mk = User.objects.create_user
        self.admin = mk('admin1', password='x', role='admin', is_staff=True)
        self.customer = mk('cust1', password='x', role='customer')
        self.other_customer = mk('cust2', password='x', role='customer')
        self.handyman = mk('hand1', password='x', role='handyman')
        self.other_handyman = mk('hand2', password='x', role='handyman')
        self.job = Job.objects.create(
            customer=self.customer, handyman=self.handyman, service_name='Plumbing',
            description='Leaking tap', address='12 Royal Road')

    def login(self, user):
        self.client.force_login(user)

    def url(self, name, *args):
        return reverse(f'jobs:{name}', args=args)

    def test_reference_is_generated(self):
        self.assertTrue(self.job.reference.startswith('JOB-'))

    def test_login_required(self):
        self.assertEqual(self.client.get(self.url('list')).status_code, 302)

    def test_visibility(self):
        self.login(self.customer)
        self.assertEqual(self.client.get(self.url('detail', self.job.pk)).status_code, 200)
        self.login(self.other_customer)
        self.assertEqual(self.client.get(self.url('detail', self.job.pk)).status_code, 404)
        self.login(self.other_handyman)
        self.assertEqual(self.client.get(self.url('detail', self.job.pk)).status_code, 404)
        self.login(self.admin)
        self.assertEqual(self.client.get(self.url('detail', self.job.pk)).status_code, 200)

    def test_clock_in_and_out(self):
        self.login(self.handyman)
        self.client.post(self.url('clock_in', self.job.pk))
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.IN_PROGRESS)
        self.assertEqual(self.job.time_logs.count(), 1)
        self.client.post(self.url('clock_in', self.job.pk))  # already clocked in
        self.assertEqual(self.job.time_logs.count(), 1)
        self.client.post(self.url('clock_out', self.job.pk))
        self.assertIsNotNone(self.job.time_logs.first().clocked_out_at)

    def test_customer_cannot_clock_in(self):
        self.login(self.customer)
        self.assertEqual(self.client.post(self.url('clock_in', self.job.pk)).status_code, 403)

    def test_other_handyman_cannot_act_on_job(self):
        self.login(self.other_handyman)
        self.assertEqual(self.client.post(self.url('clock_in', self.job.pk)).status_code, 404)

    def test_complete_needs_in_progress_and_notes(self):
        self.login(self.handyman)
        # assigned job cannot be completed
        self.client.post(self.url('complete', self.job.pk), {'completion_notes': 'Done'})
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.ASSIGNED)
        self.client.post(self.url('clock_in', self.job.pk))
        # empty notes rejected
        self.client.post(self.url('complete', self.job.pk), {'completion_notes': '  '})
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.IN_PROGRESS)
        # valid completion fires the signal and closes the open time log
        received = []
        job_completed.connect(lambda sender, job, **kw: received.append(job), weak=False,
                              dispatch_uid='test_job_completed')
        self.client.post(self.url('complete', self.job.pk), {'completion_notes': 'Replaced washer'})
        job_completed.disconnect(dispatch_uid='test_job_completed')
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.COMPLETED)
        self.assertEqual(self.job.completion_notes, 'Replaced washer')
        self.assertEqual(len(received), 1)
        self.assertFalse(self.job.time_logs.filter(clocked_out_at__isnull=True).exists())

    def test_daily_report_is_updated_not_duplicated(self):
        self.login(self.handyman)
        self.client.post(self.url('report', self.job.pk), {'details': 'Started', 'percent_complete': 20})
        self.client.post(self.url('report', self.job.pk), {'details': 'More done', 'percent_complete': 60})
        self.assertEqual(ProgressReport.objects.filter(job=self.job).count(), 1)
        self.assertEqual(ProgressReport.objects.get(job=self.job).percent_complete, 60)

    def test_report_rejects_percent_over_100(self):
        self.login(self.handyman)
        self.client.post(self.url('report', self.job.pk), {'details': 'x', 'percent_complete': 150})
        self.assertFalse(ProgressReport.objects.exists())

    def test_evidence_upload_accepts_png_only(self):
        self.login(self.handyman)
        good = SimpleUploadedFile('work.png', png_bytes(), content_type='image/png')
        self.client.post(self.url('evidence', self.job.pk), {'image': good, 'caption': 'Tap'})
        self.assertEqual(self.job.evidence.count(), 1)
        bad = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        self.client.post(self.url('evidence', self.job.pk), {'image': bad})
        self.assertEqual(self.job.evidence.count(), 1)
        ev = self.job.evidence.first()
        self.assertEqual(self.client.get(self.url('evidence_file', ev.pk)).status_code, 200)
        self.login(self.other_customer)
        self.assertEqual(self.client.get(self.url('evidence_file', ev.pk)).status_code, 404)

    def test_payout_stages(self):
        self.login(self.handyman)
        self.client.post(self.url('payout', self.job.pk, 'waiting'))  # not completed yet
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_stage, Job.PAYOUT_NONE)
        self.job.status = Job.COMPLETED
        self.job.save()
        self.client.post(self.url('payout', self.job.pk, 'finished'))  # must wait first
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_stage, Job.PAYOUT_NONE)
        self.client.post(self.url('payout', self.job.pk, 'waiting'))
        self.client.post(self.url('payout', self.job.pk, 'finished'))
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_stage, Job.PAYOUT_FINISHED)

    def test_admin_flag_needs_reason_and_can_be_removed(self):
        self.login(self.admin)
        self.client.post(self.url('flag', self.job.pk), {'reason': ''})
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_flagged)
        self.client.post(self.url('flag', self.job.pk), {'reason': 'Photos look reused'})
        self.job.refresh_from_db()
        self.assertTrue(self.job.is_flagged)
        self.assertEqual(self.job.flagged_by, self.admin)
        self.client.post(self.url('flag', self.job.pk))
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_flagged)

    def test_handyman_cannot_flag(self):
        self.login(self.handyman)
        self.assertEqual(self.client.post(self.url('flag', self.job.pk), {'reason': 'x'}).status_code, 403)

    def test_delayed_detection_and_admin_filters(self):
        self.job.due_date = timezone.localdate() - timedelta(days=2)
        self.job.save()
        fine = Job.objects.create(
            customer=self.customer, handyman=self.handyman, service_name='Painting',
            description='Walls', address='x', due_date=timezone.localdate() + timedelta(days=5))
        self.assertTrue(self.job.is_delayed)
        self.assertFalse(fine.is_delayed)
        self.login(self.admin)
        refs = [j.reference for j in self.client.get(self.url('list') + '?delayed=1').context['jobs']]
        self.assertEqual(refs, [self.job.reference])
        res = self.client.get(self.url('list') + f'?handyman={self.handyman.pk}&status=assigned')
        self.assertEqual(len(res.context['jobs']), 2)

    def test_customer_list_shows_only_own_jobs(self):
        self.login(self.other_customer)
        self.assertEqual(len(self.client.get(self.url('list')).context['jobs']), 0)

    def test_job_rejects_wrong_roles(self):
        from django.core.exceptions import ValidationError
        job = Job(customer=self.handyman, handyman=self.customer, service_name='x',
                  description='x', address='x')
        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_admin_role_without_staff_is_refused(self):
        no_staff = User.objects.create_user('admin2', password='x', role='admin')
        self.login(no_staff)
        self.assertEqual(self.client.get(self.url('list')).status_code, 403)

    def test_superuser_without_admin_role_is_not_admin(self):
        su = User.objects.create_superuser('root1', password='x')
        self.login(su)
        self.assertEqual(
            self.client.post(self.url('flag', self.job.pk), {'reason': 'x'}).status_code, 403)