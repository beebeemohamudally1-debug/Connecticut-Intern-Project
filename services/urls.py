from django.urls import path
from . import views

app_name = 'services'
urlpatterns = [
    path('search/', views.service_search, name='search'),
    path('results/', views.service_results, name='results'),
]
