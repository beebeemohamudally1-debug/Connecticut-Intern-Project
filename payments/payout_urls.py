from django.urls import path

from . import payout_views as views

# Added to payments/urls.py with:   urlpatterns += payout_urlpatterns
urlpatterns = [
    # administrator
    path('payouts/', views.payout_list, name='payout_list'),
    path('payouts/record/<int:job_id>/', views.payout_record, name='payout_record'),
    # administrator and handyman (the handyman sees only his own)
    path('payouts/<int:pk>/', views.payout_detail, name='payout_detail'),
    # handyman
    path('handyman/earnings/', views.my_earnings, name='my_earnings'),
    path('handyman/payouts/<int:pk>/confirm/', views.payout_confirm, name='payout_confirm'),
]
