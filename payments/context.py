"""Template context for handymen: `hc_subscription` is available in every template.

Add 'payments.context.handyman_subscription' to TEMPLATES -> OPTIONS -> context_processors in settings.py.
Other handyman pages can use it too, e.g. for the "Listing status" card:
    {% if hc_subscription.is_active %}Active{% else %}Not listed{% endif %}
"""
from .subscriptions import ACTIVE, STATE_LABELS, HandymanSubscription, NEW, invoice_days_before


def handyman_subscription(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated or getattr(user, 'role', None) != 'handyman':
        return {}
    subscription = HandymanSubscription.objects.filter(handyman=user).first()
    if subscription is None:
        state, expires_on, days_left, is_active = NEW, None, None, False
    else:
        state, expires_on, days_left, is_active = (subscription.state, subscription.expires_on,
                                                   subscription.days_left, subscription.is_active)
    title = text = ''
    if state == NEW:
        title, text = 'You are not subscribed yet.', 'Subscribe to be listed in search and to receive new requests.'
    elif not is_active:
        title = 'Your subscription is not active.'
        text = 'You are hidden from search and cannot take new requests until your payment is cleared.'
    elif days_left is not None and days_left <= invoice_days_before():
        when = 'today' if days_left == 0 else f"in {days_left} day{'s' if days_left != 1 else ''}"
        title = f"Your subscription ends {when}."
        text = ('Renew to stay listed.' if state == ACTIVE else
                'You cancelled it, so it will not renew. Subscribe again to stay listed.')
    return {'hc_subscription': {
        'state': state, 'state_label': STATE_LABELS[state], 'is_active': is_active, 'expires_on': expires_on,
        'days_left': days_left, 'show_banner': bool(title), 'banner_title': title, 'banner_text': text,
    }}
