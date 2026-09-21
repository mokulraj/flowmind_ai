from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "api/notifications/",
        include("apps.notifications.urls"),
    ),

    path(
        "api/audit/",
        include("apps.audit.urls"),
    ),
]