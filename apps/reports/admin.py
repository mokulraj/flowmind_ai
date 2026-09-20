from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "workflow",
        "dataset",
        "report_type",
        "status",
        "output_format",
        "created_by",
        "created_at",
    )

    list_filter = (
        "report_type",
        "status",
        "output_format",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "organization__name",
        "workflow__name",
        "dataset__name",
        "created_by__username",
        "created_by__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )