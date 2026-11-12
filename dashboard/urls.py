from django.urls import path
from .views import handyman_dashboard

urlpatterns = [
    path('', handyman_dashboard, name='handyman_dashboard'),
]

#http://127.0.0.1:8000/dashboard/