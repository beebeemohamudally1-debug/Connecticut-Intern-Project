"""Shows a new handyman the plan page the first time they open the dashboard in a session.

Add to MIDDLEWARE in settings.py, AFTER 'django.contrib.messages.middleware.MessageMiddleware':
    'payments.middleware.SubscriptionOnboardingMiddleware',

Who is sent there: a handyman who has never paid and has not cancelled. Once per login session, and only when
they open the dashboard home page, so nothing else is blocked and there is no redirect loop. Handymen who have
paid before (even if it lapsed) just see the banner on every page.
"""
from django.contrib import messages
from django.shortcuts import redirect

from .subscriptions import HandymanSubscription

DASHBOARD_VIEW = 'dashboard:handyman_dashboard'
SESSION_KEY = 'subscription_onboarding_shown'


class SubscriptionOnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        if (request.method != 'GET' or not user.is_authenticated or getattr(user, 'role', None) != 'handyman'
                or request.session.get(SESSION_KEY)):
            return None
        match = request.resolver_match
        if match is None or match.view_name != DASHBOARD_VIEW:
            return None
        subscription = HandymanSubscription.objects.filter(handyman=user).first()
        if subscription is not None and (subscription.expires_on is not None or not subscription.auto_renew):
            return None                                   # has paid before, or cancelled on purpose
        request.session[SESSION_KEY] = True
        messages.info(request, 'Welcome! Choose a plan to be listed in search and receive new requests.')
        return redirect('payments:my_subscription')
