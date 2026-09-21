from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkUnreadView,
    NotificationUnreadCountView,
)


app_name = "notifications"


urlpatterns = [
    path(
        "",
        NotificationListView.as_view(),
        name="list",
    ),
    path(
        "unread-count/",
        NotificationUnreadCountView.as_view(),
        name="unread-count",
    ),
    path(
        "<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="mark-read",
    ),
    path(
        "<int:pk>/unread/",
        NotificationMarkUnreadView.as_view(),
        name="mark-unread",
    ),
]