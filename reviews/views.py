
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from jobs.models import Job
from .forms import ReviewForm
from .models import Review


def is_admin(user):
    return user.is_superuser or (
        user.is_active and user.role == 'admin'
    )


# ==========================================
# CUSTOMER - SUBMIT REVIEW
# ==========================================

@login_required
@require_http_methods(["GET", "POST"])
def submit_review(request, job_id):
    if request.user.role != 'customer':
        raise PermissionDenied

    job = get_object_or_404(
        Job,
        pk=job_id,
        customer=request.user
    )

    if job.status != Job.COMPLETED:
        raise PermissionDenied(
            'Only completed jobs can be reviewed.'
        )

    if Review.objects.filter(job=job).exists():
        raise PermissionDenied(
            'This job has already been reviewed.'
        )

    if request.method == 'POST':
        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save(commit=False)
            review.job = job
            review.customer = request.user
            review.status = Review.PENDING
            review.save()

            return redirect('reviews:my_reviews')
    else:
        form = ReviewForm()

    return render(
        request,
        'reviews/submit_review.html',
        {
            'form': form,
            'job': job
        }
    )


# ==========================================
# CUSTOMER - REVIEW HISTORY
# ==========================================

@login_required
def my_reviews(request):
    if request.user.role != 'customer':
        raise PermissionDenied

    reviews = Review.objects.filter(
        customer=request.user
    ).select_related(
        'job'
    ).order_by('-created_at')

    return render(
        request,
        'reviews/my_reviews.html',
        {
            'reviews': reviews
        }
    )


# ==========================================
# ADMIN - VIEW ALL REVIEWS
# ==========================================

@login_required
def admin_reviews(request):
    if not is_admin(request.user):
        raise PermissionDenied

    reviews = Review.objects.select_related(
        'job',
        'customer',
        'assessed_by'
    ).order_by('-created_at')

    selected_status = request.GET.get('status', '')

    if selected_status in (
        Review.PENDING,
        Review.APPROVED,
        Review.REJECTED
    ):
        reviews = reviews.filter(
            status=selected_status
        )

    return render(
        request,
        'reviews/admin_reviews.html',
        {
            'reviews': reviews,
            'selected_status': selected_status,
            'pending_count': Review.objects.filter(
                status=Review.PENDING
            ).count(),
            'approved_count': Review.objects.filter(
                status=Review.APPROVED
            ).count(),
            'rejected_count': Review.objects.filter(
                status=Review.REJECTED
            ).count(),
        }
    )


# ==========================================
# ADMIN - REVIEW DETAILS
# ==========================================

@login_required
def review_detail(request, review_id):
    if not is_admin(request.user):
        raise PermissionDenied

    review = get_object_or_404(
        Review.objects.select_related(
            'job',
            'customer',
            'assessed_by'
        ),
        pk=review_id
    )

    return render(
        request,
        'reviews/review_detail.html',
        {
            'review': review
        }
    )


# ==========================================
# ADMIN - APPROVE REVIEW
# ==========================================

@login_required
@require_POST
def approve_review(request, review_id):
    if not is_admin(request.user):
        raise PermissionDenied

    with transaction.atomic():
        review = get_object_or_404(
            Review.objects.select_for_update(),
            pk=review_id
        )

        if review.status != Review.PENDING:
            raise PermissionDenied(
                'Only pending reviews can be assessed.'
            )

        review.status = Review.APPROVED
        review.assessed_by = request.user
        review.assessed_at = timezone.now()

        review.save(update_fields=[
            'status',
            'assessed_by',
            'assessed_at',
            'updated_at'
        ])

    return redirect(
        'reviews:review_detail',
        review_id=review.pk
    )


# ==========================================
# ADMIN - REJECT REVIEW
# ==========================================

@login_required
@require_POST
def reject_review(request, review_id):
    if not is_admin(request.user):
        raise PermissionDenied

    with transaction.atomic():
        review = get_object_or_404(
            Review.objects.select_for_update(),
            pk=review_id
        )

        if review.status != Review.PENDING:
            raise PermissionDenied(
                'Only pending reviews can be assessed.'
            )

        review.status = Review.REJECTED
        review.assessed_by = request.user
        review.assessed_at = timezone.now()

        review.save(update_fields=[
            'status',
            'assessed_by',
            'assessed_at',
            'updated_at'
        ])

    return redirect(
        'reviews:review_detail',
        review_id=review.pk
    )
