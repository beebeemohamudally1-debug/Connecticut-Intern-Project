from django.shortcuts import render
from django.http import JsonResponse
from .models import Service


def service_search(request):
    qs = Service.objects.active().search(request.GET.get('q'))
    category = request.GET.get('category')
    if category:
        qs = qs.filter(category__name__iexact=category)
    results = [
        {'id': s.pk, 'name': s.name, 'category': s.category.name}
        for s in qs.select_related('category')
    ]
    return JsonResponse({'results': results})


def service_results(request):
    """Public page: approved professionals filtered by category, area and skill (all optional GET params)."""
    from accounts.models import HandymanProfile
    from .models import ServiceArea, ServiceCategory, Skill

    category = request.GET.get('category', '').strip()
    region = request.GET.get('region', '').strip()
    skills_sel = request.GET.getlist('skill')
    areas_sel = request.GET.getlist('area')
    qs = HandymanProfile.objects.filter(status=HandymanProfile.STATUS_ACTIVE, user__is_active=True, user__is_suspended=False).select_related('user')
    if category:
        qs = qs.filter(categories__name__iexact=category)
    if region:
        qs = qs.filter(service_areas__name__iexact=region)
    if skills_sel:
        qs = qs.filter(skills__name__in=skills_sel)
    if areas_sel:
        qs = qs.filter(service_areas__name__in=areas_sel)
    qs = qs.distinct()
    pros = []
    for p in qs[:30]:
        name = p.user.get_full_name() or p.user.username
        parts = name.split()
        pros.append({'name': name, 'initials': ''.join(w[0] for w in (parts[:1] + parts[-1:])).upper()[:2],
                     'summary': p.bio or 'Verified professional on HandyConnect.', 'verified': True})
    cat_obj = ServiceCategory.objects.filter(name__iexact=category).first()
    skills = Skill.objects.filter(is_active=True, **({'category': cat_obj} if cat_obj else {}))
    return render(request, 'services/service_results.html', {
        'category': category, 'region': region, 'f': request.GET, 'professionals': pros, 'total': len(pros), 'shown': len(pros),
        'categories': list(ServiceCategory.objects.filter(is_active=True).values_list('name', flat=True)),
        'regions': list(ServiceArea.objects.filter(is_active=True).values_list('name', flat=True)),
        'skills': [{'label': s.name, 'checked': s.name in skills_sel} for s in skills],
        'areas': [{'label': a.name, 'checked': a.name in areas_sel} for a in ServiceArea.objects.filter(is_active=True)]})
