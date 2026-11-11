from django.shortcuts import render

# Create your views here.
def handyman_dashboard(request):
    return render(request, 'dashboard/handyman_dashboard.html')