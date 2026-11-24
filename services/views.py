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
# Create your views here.
