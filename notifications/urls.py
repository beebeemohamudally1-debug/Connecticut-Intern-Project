
from django.urls import path
from . import views

urlpatterns = [
    path(
        '',
        views.notification_list,
        name='notification_list'
    ),
    path(
        'unread-count/',
        views.unread_count,
        name='unread_count'
    ),
    path(
        '<int:notification_id>/read/',
        views.mark_as_read,
        name='mark_as_read'
    ),
    path(
        'read-all/',
        views.mark_all_as_read,
        name='mark_all_as_read'
    ),
]
