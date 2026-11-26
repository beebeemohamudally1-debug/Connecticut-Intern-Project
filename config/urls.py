"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views
import re
from django.conf import settings
from django.http import Http404
from django.urls import re_path
from django.views.static import serve

urlpatterns = [
    path('dev/', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('notifications/', include('notifications.urls')),
    path('payments/', include('payments.urls')),
    path('bookings/', include('bookings.urls')),
    path('jobs/', include('jobs.urls')),
    path('complaints/', include('complaints.urls')),
    path('admin-portal/', include('accounts.admin_urls')),
    path('dashboard/', include('dashboard.urls')),
    path('reports/', include('reports.urls')),
    path('', include('accounts.urls')),
    path('reviews/', include('reviews.urls')),
    path('services/', include('services.urls')),
    path('customer/', include('customer_portal.urls')),
]


PRIVATE_MEDIA_FOLDERS = {'handyman_documents'}


def public_media(request, path):
    """Development only: serve uploaded media, but never the private handyman documents.
    Those are opened only through the administrator-only document view."""
    parts = [p.strip().rstrip('. ').lower() for p in re.split(r'[\\/]+', path)]
    if PRIVATE_MEDIA_FOLDERS.intersection(parts):
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += [re_path(r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')), public_media)]
