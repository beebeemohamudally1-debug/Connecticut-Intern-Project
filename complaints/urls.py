from django.urls import path

from . import views

app_name = 'complaints'

urlpatterns = [
    path('', views.complaint_list, name='list'),
    path('new/', views.complaint_create, name='create'),
    path('<int:pk>/', views.complaint_detail, name='detail'),
    path('<int:pk>/reply/', views.complaint_reply, name='reply'),
    path('<int:pk>/enquiry/', views.complaint_enquiry, name='enquiry'),
    path('<int:pk>/resolution/', views.complaint_resolution, name='resolution'),
    path('evidence/<int:pk>/file/', views.evidence_file, name='evidence_file'),
]
