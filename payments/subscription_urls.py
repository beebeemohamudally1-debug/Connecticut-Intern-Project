from django.urls import path

from . import subscription_views as views

urlpatterns = [
    # administrator: handyman subscriptions
    path('subscriptions/', views.subscription_list, name='subscription_list'),
    path('subscriptions/<int:handyman_id>/invoice/', views.subscription_issue_invoice, name='subscription_issue_invoice'),
    path('subscriptions/<int:handyman_id>/extend/', views.subscription_extend, name='subscription_extend'),
    # handyman
    path('handyman/subscription/', views.my_subscription, name='my_subscription'),
    path('handyman/subscription/subscribe/', views.subscription_subscribe, name='subscription_subscribe'),
    path('handyman/subscription/cancel/', views.subscription_cancel, name='subscription_cancel'),
    path('handyman/subscription/receipts/<int:pk>/', views.subscription_receipt, name='subscription_receipt'),
]
