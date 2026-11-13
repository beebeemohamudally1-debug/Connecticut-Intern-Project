from django.urls import path

from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('<int:pk>/', views.job_detail, name='detail'),
    path('<int:pk>/clock-in/', views.clock_in, name='clock_in'),
    path('<int:pk>/clock-out/', views.clock_out, name='clock_out'),
    path('<int:pk>/report/', views.submit_report, name='report'),
    path('<int:pk>/evidence/', views.upload_evidence, name='evidence'),
    path('<int:pk>/complete/', views.complete_job, name='complete'),
    path('<int:pk>/payout/<slug:stage>/', views.payout_stage, name='payout'),
    path('<int:pk>/flag/', views.flag_job, name='flag'),
    path('evidence/<int:pk>/file/', views.evidence_file, name='evidence_file'),
]
