from django.conf import settings
from django.urls import NoReverseMatch, reverse


def _logout_url():
    """Where the Log out button posts to. Set HANDYMAN_LOGOUT_URL in settings.py to override."""
    custom = getattr(settings, 'HANDYMAN_LOGOUT_URL', None)
    if custom:
        return custom
    for name in ('logout', 'accounts:logout', 'accounts_logout', 'user_logout', 'accounts:user_logout'):
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    return '/logout/'


def handyman_user(request):
    """Adds the logged-in person's name, initials and the logout URL to every template."""
    data = {'hc_logout_url': _logout_url()}
    u = getattr(request, 'user', None)
    if not u or not u.is_authenticated:
        return data
    name = (u.get_full_name() or u.get_username() or '').strip().split('@')[0]
    parts = name.replace('.', ' ').replace('_', ' ').split()
    data.update({
        'hc_uid': u.pk,
        'hc_name': ' '.join(p.title() for p in parts) or 'User',
        'hc_first': parts[0].title() if parts else 'there',
        'hc_initials': ''.join(p[0] for p in parts[:2]).upper() or 'U',
    })
    return data