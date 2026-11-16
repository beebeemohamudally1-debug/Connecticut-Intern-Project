
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

from jobs.models import Job
from .models import Review


User = get_user_model()


class ReviewTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username='review_customer',
            password='TestPass123!',
            role='customer'
        )

        self.other_customer = User.objects.create_user(
            username='other_customer',
            password='TestPass123!',
            role='customer'
        )

        self.handyman = User.objects.create_user(
            username='review_handyman',
            password='TestPass123!',
            role='handyman'
        )

        self.admin_user = User.objects.create_user(
            username='review_admin',
            password='TestPass123!',
            role='admin'
        )

        self.job = Job.objects.create(
            customer=self.customer,
            handyman=self.handyman,
            service_name='Plumbing',
            description='Fix leaking pipe',
            address='Port Louis',
            status=Job.COMPLETED,
            completed_at=timezone.now()
        )

    def create_review(self, status=Review.PENDING):
        return Review.objects.create(
            job=self.job,
            customer=self.customer,
            rating=5,
            comment='Excellent service',
            status=status
        )

    # CUSTOMER TESTS

    def test_customer_can_submit_review(self):
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('reviews:submit_review', args=[self.job.pk]),
            {
                'rating': 5,
                'comment': 'Excellent service'
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.first()
        self.assertEqual(review.customer, self.customer)
        self.assertEqual(review.job, self.job)
        self.assertEqual(review.status, Review.PENDING)

    def test_customer_cannot_review_incomplete_job(self):
        self.job.status = Job.IN_PROGRESS
        self.job.save()

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('reviews:submit_review', args=[self.job.pk]),
            {
                'rating': 5,
                'comment': 'Good service'
            }
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 0)

    def test_customer_cannot_review_another_customers_job(self):
        self.client.force_login(self.other_customer)

        response = self.client.post(
            reverse('reviews:submit_review', args=[self.job.pk]),
            {
                'rating': 5,
                'comment': 'Good service'
            }
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Review.objects.count(), 0)

    def test_duplicate_review_is_prevented(self):
        self.create_review()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('reviews:submit_review', args=[self.job.pk]),
            {
                'rating': 4,
                'comment': 'Second review'
            }
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 1)

    def test_rating_below_one_is_invalid(self):
        review = Review(
            job=self.job,
            customer=self.customer,
            rating=0,
            comment='Invalid rating'
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_rating_above_five_is_invalid(self):
        review = Review(
            job=self.job,
            customer=self.customer,
            rating=6,
            comment='Invalid rating'
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_requires_completed_job(self):
        self.job.status = Job.ASSIGNED
        self.job.save()

        review = Review(
            job=self.job,
            customer=self.customer,
            rating=5,
            comment='Test review'
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_requires_correct_customer(self):
        review = Review(
            job=self.job,
            customer=self.other_customer,
            rating=5,
            comment='Test review'
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_customer_can_view_review_history(self):
        self.create_review()
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse('reviews:my_reviews')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context['reviews']), 1
        )

    def test_customer_cannot_view_other_reviews(self):
        self.create_review()
        self.client.force_login(self.other_customer)

        response = self.client.get(
            reverse('reviews:my_reviews')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context['reviews']), 0
        )

    def test_handyman_cannot_submit_review(self):
        self.client.force_login(self.handyman)

        response = self.client.post(
            reverse('reviews:submit_review', args=[self.job.pk]),
            {
                'rating': 5,
                'comment': 'Test review'
            }
        )

        self.assertEqual(response.status_code, 403)

    # ADMIN TESTS

    def test_admin_can_view_all_reviews(self):
        self.create_review()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('reviews:admin_reviews')
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context['reviews']), 1
        )

    def test_admin_can_filter_pending_reviews(self):
        self.create_review()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('reviews:admin_reviews'),
            {'status': Review.PENDING}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context['reviews']), 1
        )

    def test_admin_can_view_review_detail(self):
        review = self.create_review()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('reviews:review_detail', args=[review.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['review'], review)

    def test_admin_can_approve_review(self):
        review = self.create_review()
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse('reviews:approve_review', args=[review.pk])
        )

        review.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(review.status, Review.APPROVED)
        self.assertEqual(review.assessed_by, self.admin_user)
        self.assertIsNotNone(review.assessed_at)

    def test_admin_can_reject_review(self):
        review = self.create_review()
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse('reviews:reject_review', args=[review.pk])
        )

        review.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(review.status, Review.REJECTED)
        self.assertEqual(review.assessed_by, self.admin_user)

    def test_customer_cannot_approve_review(self):
        review = self.create_review()
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('reviews:approve_review', args=[review.pk])
        )

        self.assertEqual(response.status_code, 403)

        review.refresh_from_db()
        self.assertEqual(review.status, Review.PENDING)

    def test_handyman_cannot_reject_review(self):
        review = self.create_review()
        self.client.force_login(self.handyman)

        response = self.client.post(
            reverse('reviews:reject_review', args=[review.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_approval_requires_post(self):
        review = self.create_review()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('reviews:approve_review', args=[review.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_rejection_requires_post(self):
        review = self.create_review()
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse('reviews:reject_review', args=[review.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_approved_review_cannot_be_reassessed(self):
        review = self.create_review(status=Review.APPROVED)
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse('reviews:reject_review', args=[review.pk])
        )

        self.assertEqual(response.status_code, 403)

        review.refresh_from_db()
        self.assertEqual(review.status, Review.APPROVED)

    def test_unauthenticated_user_redirected(self):
        response = self.client.get(
            reverse('reviews:my_reviews')
        )

        self.assertEqual(response.status_code, 302)

