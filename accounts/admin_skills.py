"""Admin portal - Manage Skills: real data from services.Skill, accounts.HandymanProfile and
bookings.HandymanProfileRequest (request_type = skill).

These views only READ the database to show the pages (admin only).
BACKEND (services): there are no views yet that add, edit, deactivate or reactivate a skill, or
approve / reject a handyman's skill request, so those buttons save nothing and show a demo
message. The places to connect are marked "BACKEND" below and in the templates.
"""
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from accounts.models import HandymanProfile
from bookings.models import HandymanProfileRequest
from dashboard.permissions import role_required
from services.models import ServiceCategory, Skill

from .admin_views import _initials, _person_name

PAGE_SIZE = 5
REQ = HandymanProfileRequest
# Words used on the pages for the request actions (the model says Add / Modify / Remove)
ACTION_LABEL = {REQ.ACTION_ADD: 'Add', REQ.ACTION_MODIFY: 'Change', REQ.ACTION_REMOVE: 'Remove'}
STATUS_TONE = {REQ.STATUS_PENDING: 'wait', REQ.STATUS_APPROVED: 'on', REQ.STATUS_REJECTED: 'bad'}
PROFILE_TONE = {HandymanProfile.STATUS_ACTIVE: 'on', HandymanProfile.STATUS_PENDING: 'wait',
                HandymanProfile.STATUS_REJECTED: 'bad'}
PROFILE_LABEL = {HandymanProfile.STATUS_ACTIVE: 'Approved', HandymanProfile.STATUS_PENDING: 'Pending',
                 HandymanProfile.STATUS_REJECTED: 'Rejected'}


def _skill_ref(skill):
    return f'SKL-{skill.pk:03d}'


def _request_ref(r):
    return f'SKR-{100 + r.pk}'


def _skill_requests():
    return REQ.objects.filter(request_type=REQ.TYPE_SKILL).select_related('handyman')


def _request_skill(r):
    """The skill a request is about: the new name for Add / Change, the current one for Remove."""
    return r.requested_value or r.current_value


def _categories():
    return list(ServiceCategory.objects.order_by('name').values_list('name', flat=True))


@role_required('admin')
def skills(request):
    """Skills list: totals, search, category / status filters and pages (filters work in the browser)."""
    qs = Skill.objects.select_related('category').annotate(handymen_count=Count('handymen')).order_by('name')
    rows = [{
        'name': s.name,
        'category': s.category.name if s.category else '',
        'handymen': s.handymen_count,
        'active': s.is_active,
        'view_url': reverse('accounts_admin:skill_detail', args=[s.pk]),
        'edit_url': reverse('accounts_admin:skill_edit', args=[s.pk]),
    } for s in qs]
    page = {
        'stats': {
            'total': len(rows),
            'active': sum(1 for r in rows if r['active']),
            'inactive': sum(1 for r in rows if not r['active']),
            'pending': _skill_requests().filter(status=REQ.STATUS_PENDING).count(),
        },
        'rows': rows,
        'categories': _categories(),
        'page_size': PAGE_SIZE,
    }
    return render(request, 'services/admin_skills.html', {'page': page})


@role_required('admin')
def skill_detail(request, pk):
    """One skill: overview, the handymen who have it, Edit and Deactivate / Reactivate (demo)."""
    skill = get_object_or_404(Skill.objects.select_related('category'), pk=pk)
    profiles = (skill.handymen.select_related('user', 'user__region')
                .prefetch_related('service_areas').order_by('user__first_name', 'user__last_name'))
    handymen = [{
        'name': _person_name(p.user),
        'initials': _initials(p.user),
        'areas': ', '.join(a.name for a in p.service_areas.all()) or (p.user.region.name if p.user.region else ''),
        'status': PROFILE_LABEL.get(p.status, p.get_status_display()),
        'tone': PROFILE_TONE.get(p.status, 'wait'),
        'url': reverse('accounts_admin:handyman_profile', args=[p.user.pk]),
    } for p in profiles]
    page = {
        'ref': _skill_ref(skill),
        'name': skill.name,
        'category': skill.category.name if skill.category else '',
        'active': skill.is_active,
        'handymen': handymen,
        'pending': _skill_requests().filter(status=REQ.STATUS_PENDING, requested_value__iexact=skill.name).count(),
        'edit_url': reverse('accounts_admin:skill_edit', args=[skill.pk]),
    }
    return render(request, 'services/admin_skill_detail.html', {'page': page})


@role_required('admin')
def skill_form(request, pk=None):
    """Add Skill (no pk) or Edit Skill. BACKEND: the form is a demo, nothing is saved yet."""
    skill = get_object_or_404(Skill.objects.select_related('category'), pk=pk) if pk else None
    page = {
        'editing': bool(skill),
        'ref': _skill_ref(skill) if skill else '',
        'name': skill.name if skill else '',
        'category': skill.category.name if skill and skill.category else '',
        'active': skill.is_active if skill else True,
        'categories': _categories(),
        # Names already used, so the browser can warn before "saving" (Skill.name is unique)
        'taken': list(Skill.objects.exclude(pk=pk).values_list('name', flat=True)),
        'back_url': reverse('accounts_admin:skill_detail', args=[skill.pk]) if skill else reverse('accounts_admin:skills'),
    }
    return render(request, 'services/admin_skill_form.html', {'page': page})


@role_required('admin')
def skill_requests(request):
    """Handyman skill requests: search, status / type filters and pages (filters work in the browser)."""
    rows = [{
        'ref': _request_ref(r),
        'handyman': _person_name(r.handyman),
        'skill': _request_skill(r),
        'current': r.current_value if r.action == REQ.ACTION_MODIFY else '',
        'action': r.action,
        'action_label': ACTION_LABEL.get(r.action, r.get_action_display()),
        'status': r.status,
        'status_label': r.get_status_display(),
        'submitted': f'{r.submitted_at:%d %b %Y}',
        'url': reverse('accounts_admin:skill_request_detail', args=[r.pk]),
    } for r in _skill_requests().order_by('-submitted_at')]
    page = {
        'rows': rows,
        'pending': sum(1 for r in rows if r['status'] == REQ.STATUS_PENDING),
        'statuses': REQ.STATUS_CHOICES,
        'actions': ACTION_LABEL,
        'page_size': PAGE_SIZE,
    }
    return render(request, 'services/admin_skill_requests.html', {'page': page})


@role_required('admin')
def skill_request_detail(request, pk):
    """One skill request: summary, the handyman's profile and the decision (Approve / Reject are a demo)."""
    r = get_object_or_404(_skill_requests().select_related('reviewed_by', 'handyman__region'), pk=pk)
    name = _request_skill(r)
    skill = Skill.objects.select_related('category').filter(name__iexact=name).first()
    profile = HandymanProfile.objects.filter(user=r.handyman).first()
    page = {
        'ref': _request_ref(r),
        'handyman': _person_name(r.handyman),
        'initials': _initials(r.handyman),
        'handyman_url': reverse('accounts_admin:handyman_profile', args=[r.handyman.pk]),
        'region': r.handyman.region.name if r.handyman.region else '',
        'profile_status': PROFILE_LABEL.get(profile.status, '') if profile else '',
        'profile_tone': PROFILE_TONE.get(profile.status, 'wait') if profile else 'wait',
        'skill_count': profile.skills.count() if profile else 0,
        'action': r.action,
        'action_label': ACTION_LABEL.get(r.action, r.get_action_display()),
        'current': r.current_value,
        'requested': r.requested_value,
        'skill': name,
        # The request stores the skill as text; when it matches a skill in the catalogue, link to it
        'skill_url': reverse('accounts_admin:skill_detail', args=[skill.pk]) if skill else '',
        'category': skill.category.name if skill and skill.category else '',
        'submitted': f'{r.submitted_at:%d %b %Y}',
        'reason': r.reason,
        'status_label': r.get_status_display(),
        'tone': STATUS_TONE.get(r.status, 'wait'),
        'pending': r.status == REQ.STATUS_PENDING,
        'admin_note': r.admin_note,
        'reviewed': f'{r.reviewed_at:%d %b %Y}' if r.reviewed_at else '',
        'reviewed_by': _person_name(r.reviewed_by) if r.reviewed_by else '',
    }
    return render(request, 'services/admin_skill_request_detail.html', {'page': page})