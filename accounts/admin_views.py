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

# Sample data for Manage Users until the real accounts are connected
USERS_PAGE = {
    'stats': {'total': '1,284', 'customers': 842, 'handymen': 442, 'pending': 18},
    'users': [
        {'name': 'Sarah Thompson', 'initials': 'ST', 'role': 'Customer', 'email': 'sarah.thompson@email.com', 'status': 'Active', 'url': '/admin-portal/users/customer/'},
        {'name': 'Marcus Reed', 'initials': 'MR', 'role': 'Handyman', 'email': 'marcus.reed@email.com', 'status': 'Active', 'url': '/admin-portal/users/handyman/'},
        {'name': 'Daniel Brooks', 'initials': 'DB', 'role': 'Customer', 'email': 'daniel.brooks@email.com', 'status': 'Suspended', 'url': '/admin-portal/users/customer/suspended/'},
        {'name': 'Amir Patel', 'initials': 'AP', 'role': 'Handyman', 'email': 'amir.patel@email.com', 'status': 'Pending', 'url': '/admin-portal/users/handyman/verify/'},
        {'name': 'Emma Wilson', 'initials': 'EW', 'role': 'Customer', 'email': 'emma.wilson@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Priya Nair', 'initials': 'PN', 'role': 'Customer', 'email': 'priya.nair@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Kevin Dubois', 'initials': 'KD', 'role': 'Handyman', 'email': 'kevin.dubois@email.com', 'status': 'Pending', 'url': '#'},
        {'name': 'Aisha Rahman', 'initials': 'AR', 'role': 'Customer', 'email': 'aisha.rahman@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Jean Laval', 'initials': 'JL', 'role': 'Handyman', 'email': 'jean.laval@email.com', 'status': 'Suspended', 'url': '/admin-portal/users/handyman/suspended/'},
        {'name': 'Nadia Bhuruth', 'initials': 'NB', 'role': 'Customer', 'email': 'nadia.bhuruth@email.com', 'status': 'Active', 'url': '#'},
        {'name': 'Ravi Gopaul', 'initials': 'RG', 'role': 'Handyman', 'email': 'ravi.gopaul@email.com', 'status': 'Active', 'url': '#'},
    ],
}


def users(request):
    """Manage Users."""
    return render(request, 'accounts/admin_users.html', {'page': USERS_PAGE})



# Sample data for the Customer Details page
CUSTOMER = {
    'kind': 'customer',
    'name': 'Sarah Thompson',
    'initials': 'ST',
    'id': 'USR-0042',
    'registered': '12 March 2026',
    'email': 'sarah.thompson@email.com',
    'phone': '+230 5 987 6543',
    'address': 'Quatre Bornes, Mauritius',
    'status': 'Active',
    'counts': {'submitted': '08', 'completed': '05', 'pending': '02', 'cancelled': '01'},
    'requests': [
        {'id': 'REQ-2086', 'title': 'Bathroom plumbing', 'status': 'Pending'},
        {'id': 'REQ-2073', 'title': 'Electrical repair', 'status': 'Completed'},
        {'id': 'REQ-2044', 'title': 'Tap replacement', 'status': 'Completed'},
        {'id': 'REQ-2031', 'title': 'Door lock repair', 'status': 'Completed'},
        {'id': 'REQ-2019', 'title': 'Ceiling fan installation', 'status': 'Cancelled'},
        {'id': 'REQ-1998', 'title': 'Kitchen sink unblocking', 'status': 'Completed'},
        {'id': 'REQ-1974', 'title': 'Wall painting', 'status': 'Pending'},
        {'id': 'REQ-1952', 'title': 'Light fitting', 'status': 'Completed'},
    ],
}

# Sample data for the Handyman Profile page
HANDYMAN = {
    'kind': 'handyman',
    'name': 'Marcus Reed',
    'initials': 'MR',
    'id': 'USR-0874',
    'verified': True,
    'status': 'Active',
    'email': 'marcus.reed@email.com',
    'phone': '+230 5 731 1145',
    'areas': 'Port Louis · Pamplemousses',
    'availability': 'Mon–Sat · 08:00–17:00',
    'registered': '13 May 2026',
    'completed': '48',
    'assigned': '03',
    'skills': ['Bathroom plumbing', 'Water heater repair', 'Pipe installation'],
    'services': ['Bathroom plumbing', 'Pipe leak repair', 'Water heater installation', 'General plumbing maintenance'],
}

# Sample data for a suspended customer (the page shows Reactivate instead of Suspend)
SUSPENDED_CUSTOMER = {
    'kind': 'customer',
    'name': 'Daniel Brooks',
    'initials': 'DB',
    'id': 'USR-0057',
    'registered': '04 February 2026',
    'email': 'daniel.brooks@email.com',
    'phone': '+230 5 412 7788',
    'address': 'Curepipe, Mauritius',
    'status': 'Suspended',
    'counts': {'submitted': '03', 'completed': '01', 'pending': '01', 'cancelled': '01'},
    'requests': [
        {'id': 'REQ-2062', 'title': 'Door lock repair', 'status': 'Pending'},
        {'id': 'REQ-2011', 'title': 'Ceiling fan installation', 'status': 'Cancelled'},
        {'id': 'REQ-1969', 'title': 'Tap replacement', 'status': 'Completed'},
    ],
}

# Sample data for a suspended handyman
SUSPENDED_HANDYMAN = {
    'kind': 'handyman',
    'name': 'Jean Laval',
    'initials': 'JL',
    'id': 'USR-0912',
    'verified': True,
    'status': 'Suspended',
    'email': 'jean.laval@email.com',
    'phone': '+230 5 644 2091',
    'areas': 'Curepipe · Quatre Bornes',
    'availability': 'Mon–Fri · 09:00–16:00',
    'registered': '21 June 2026',
    'completed': '12',
    'assigned': '00',
    'skills': ['Electrical repair', 'Light fitting'],
    'services': ['Electrical repair', 'Light fitting installation'],
}

# Sample data for the Registration Verification page
APPLICANT = {
    'id': 'HND-0184',
    'name': 'Amir Patel',
    'email': 'amir.patel@email.com',
    'submitted': '03 Nov 2026',
    'status': 'Pending',
    'documents': [
        {'title': 'National Identity Card', 'file': 'identity-card.pdf', 'action': 'View document'},
        {'title': 'Trade qualification', 'file': 'plumbing-certificate.pdf', 'action': 'View document'},
        {'title': 'Proof of address', 'file': 'proof-of-address.pdf', 'action': 'View document'},
        {'title': 'Profile photograph', 'file': 'handyman-photo.jpg', 'action': 'View image'},
        {'title': 'Police character certificate', 'file': 'police-certificate.pdf', 'action': 'View document'},
        {'title': 'Reference letter', 'file': 'reference-letter.pdf', 'action': 'View document'},
    ],
}


# The same page for a handyman who was already approved (opened from the profile)
APPROVED_APPLICANT = {
    'id': 'USR-0874',
    'name': 'Marcus Reed',
    'email': 'marcus.reed@email.com',
    'submitted': '10 May 2026',
    'status': 'Approved',
    'decided': '13 May 2026',
    'notes': 'All documents checked and valid.',
    'documents': APPLICANT['documents'],
}


def customer_detail(request):
    """Customer Details."""
    return render(request, 'accounts/admin_customer_detail.html', {'customer': CUSTOMER})


def handyman_profile(request):
    """Handyman Profile."""
    return render(request, 'accounts/admin_handyman_profile.html', {'handyman': HANDYMAN})


def handyman_verify(request):
    """Handyman Registration Verification."""
    return render(request, 'accounts/admin_handyman_verify.html', {'applicant': APPLICANT})


def handyman_documents(request):
    """Registration documents of an already approved handyman (read only)."""
    return render(request, 'accounts/admin_handyman_verify.html', {'applicant': APPROVED_APPLICANT})


def suspended_customer(request):
    """Customer Details for a suspended account."""
    return render(request, 'accounts/admin_customer_detail.html', {'customer': SUSPENDED_CUSTOMER})


def suspended_handyman(request):
    """Handyman Profile for a suspended account."""
    return render(request, 'accounts/admin_handyman_profile.html', {'handyman': SUSPENDED_HANDYMAN})