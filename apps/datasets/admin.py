from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Dataset
from .services.dataset_service import DatasetService


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "workflow",
        "status",
        "row_count",
        "column_count",
        "quality_score",
        "uploaded_by",
        "uploaded_at",
    )

    list_filter = (
        "status",
        "organization",
        "workflow",
    )

    search_fields = (
        "name",
        "description",
        "organization__name",
        "workflow__name",
        "uploaded_by__email",
    )

    readonly_fields = (
        "file_size",
        "row_count",
        "column_count",
        "missing_cells",
        "missing_percentage",
        "duplicate_rows",
        "duplicate_percentage",
        "quality_score",
        "validation_message",
        "uploaded_at",
        "validated_at",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "organization",
        "workflow",
        "uploaded_by",
    )

    ordering = (
        "-created_at",
    )

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

        try:
            DatasetService.validate_dataset(obj)

        except ValidationError as exc:
            self.message_user(
                request,
                str(exc),
                level="error",
            )