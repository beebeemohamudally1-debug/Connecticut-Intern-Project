"""Template filter for the admin pages: does a job need materials?

    {% load admin_materials %}
    {% with mats=q.request|materials_state %}{{ mats.label }}{% endwith %}   -> state: requested / none / waiting

The rule is in accounts/admin_payments.py (materials_state): a material request with estimated cost 0
means "no materials needed".
"""
from django import template

from accounts.admin_payments import materials_state as _materials_state

register = template.Library()


@register.filter
def materials_state(service_request):
    return _materials_state(service_request) if service_request else {'state': '', 'label': '', 'note': ''}
