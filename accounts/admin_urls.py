from django.urls import path
from . import admin_views as views

app_name = 'accounts_admin'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
]