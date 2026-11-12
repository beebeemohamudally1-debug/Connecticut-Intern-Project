from django.shortcuts import render

# Sample data until the real administrator is connected
ADMIN_PROFILE = {
    'name': 'Admin User',
    'initials': 'AU',
    'email': 'admin@handyconnect.example',
    'role': 'Administrator',
    'status': 'Active',
}

def profile(request):
    """Admin Profile."""
    return render(request, 'accounts/admin_profile.html', {'admin': ADMIN_PROFILE})