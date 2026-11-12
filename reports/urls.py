
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path(
        'job-summary/',
        views.job_summary_report,
        name='job_summary'
    ),
]
