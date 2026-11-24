
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('mine/', views.my_notification_list, name='my_notification_list'),
    path('mine/unread-count/', views.my_unread_count, name='my_unread_count'),
    path('mine/<int:notification_id>/read/', views.mark_my_notification_read, name='mark_my_notification_read'),
    path('mine/read-all/', views.mark_my_notifications_read, name='mark_my_notifications_read'),
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
