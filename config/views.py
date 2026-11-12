from django.shortcuts import render


def home(request):
    """Show the main entry points for HandyConnect."""
    return render(request, 'home.html')
