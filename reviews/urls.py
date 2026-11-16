
from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # Customer
    path(
        'submit/<int:job_id>/',
        views.submit_review,
        name='submit_review'
    ),
    path(
        'my-reviews/',
        views.my_reviews,
        name='my_reviews'
    ),

    # Administrator
    path(
        'admin/',
        views.admin_reviews,
        name='admin_reviews'
    ),
    path(
        'admin/<int:review_id>/',
        views.review_detail,
        name='review_detail'
    ),
    path(
        'admin/<int:review_id>/approve/',
        views.approve_review,
        name='approve_review'
    ),
    path(
        'admin/<int:review_id>/reject/',
        views.reject_review,
        name='reject_review'
    ),
]
